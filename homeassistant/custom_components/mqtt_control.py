"""
Publish simple item state changes via MQTT.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/mqtt_statestream/
"""
import json

import voluptuous as vol

from homeassistant.const import (CONF_DOMAINS, CONF_ENTITIES, CONF_EXCLUDE,
                                 CONF_INCLUDE, MATCH_ALL, SERVICE_TURN_ON, 
                                 SERVICE_TURN_OFF, ATTR_ENTITY_ID, SERVICE_LOCK,
                                 SERVICE_UNLOCK)
from homeassistant.core import callback
from homeassistant.components import mqtt
from homeassistant.helpers.entityfilter import generate_filter
from homeassistant.helpers.event import async_track_state_change
from homeassistant.helpers.json import JSONEncoder
import homeassistant.helpers.config_validation as cv
from homeassistant.loader import bind_hass
import homeassistant.components.switch.mqtt as mqtt_switch
import homeassistant.components.lock.mqtt as mqtt_lock

CONF_BASE_TOPIC = 'base_topic'
DEPENDENCIES = ['mqtt']
DOMAIN = 'mqtt_control'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_EXCLUDE, default={}): vol.Schema({
            vol.Optional(CONF_ENTITIES, default=[]): cv.entity_ids,
            vol.Optional(CONF_DOMAINS, default=[]):
                vol.All(cv.ensure_list, [cv.string])
        }),
        vol.Optional(CONF_INCLUDE, default={}): vol.Schema({
            vol.Optional(CONF_ENTITIES, default=[]): cv.entity_ids,
            vol.Optional(CONF_DOMAINS, default=[]):
                vol.All(cv.ensure_list, [cv.string])
        }),
        vol.Required(CONF_BASE_TOPIC): mqtt.valid_publish_topic
    })
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass, config):
    """Set up the MQTT state feed."""
    conf = config.get(DOMAIN, {})
    base_topic = conf.get(CONF_BASE_TOPIC)
    entity_include = conf.get(CONF_INCLUDE, {})
    entity_exclude = conf.get(CONF_EXCLUDE, {})
    entity_filter = generate_filter(entity_include.get(CONF_DOMAINS, []),
                                    entity_include.get(CONF_ENTITIES, []),
                                    entity_exclude.get(CONF_DOMAINS, []),
                                    entity_exclude.get(CONF_ENTITIES, []))

    if not base_topic.endswith('/'):
        base_topic = base_topic + '/'

    @callback
    def _state_publisher(entity_id, old_state, new_state):
        if new_state is None:
            return

        if not entity_filter(entity_id):
            return

        entity_id_parts = entity_id.split('.')
        domain = entity_id_parts[0]

        mybase = base_topic + entity_id.replace('.', '/') + '/state'

        if domain == 'switch' or domain == 'binary_sensor':
            payload = None
            if new_state.state == 'on':
                payload = 'ON'
            elif new_state.state == 'off':
                payload = 'OFF'
            hass.components.mqtt.async_publish(mybase, payload, 1, True)
        elif domain == 'light':
            data = {}
            if new_state.state == 'on':
                data['state'] = 'ON'
            elif new_state.state == 'off':
                data['state'] = 'OFF'
            try:
                data['brightness'] = new_state.attributes['brightness']
            except KeyError:
                pass
            payload = json.dumps(data, cls=JSONEncoder)
            hass.components.mqtt.async_publish(mybase, payload, 1, True)
        elif domain == 'lock':
            payload = None
            if new_state.state == 'locked':
                payload = 'LOCK'
            elif new_state.state == 'unlocked':
                payload = 'UNLOCK'
            hass.components.mqtt.async_publish(mybase, payload, 1, True)
        elif domain == 'sensor':
            hass.components.mqtt.async_publish(mybase, new_state.state, 1, True)

    @callback
    def _state_message_received(topic, payload, qos):
        """Handle new MQTT state messages."""
        # Parse entity from topic
        topic_parts = topic.split('/')
        domain = topic_parts[-3]
        entity = topic_parts[-2]

        entity_id = "{0}.{1}".format(domain, entity)
        if not entity_filter(entity_id):
            return

        
        data = {ATTR_ENTITY_ID: entity_id}
        if domain == 'switch':
            if payload == mqtt_switch.DEFAULT_PAYLOAD_ON:
                hass.async_add_job(hass.services.async_call(domain, SERVICE_TURN_ON, data))
            if payload == mqtt_switch.DEFAULT_PAYLOAD_OFF:
                hass.async_add_job(hass.services.async_call(domain, SERVICE_TURN_OFF, data))
        elif domain == 'light':
            payload = json.loads(payload)
            if payload['state'] == 'ON':
                try:
                    data['brightness'] = payload['brightness']
                except KeyError:
                    pass
                hass.async_add_job(hass.services.async_call(domain, SERVICE_TURN_ON, data))
            if payload['state'] == 'OFF':
                hass.async_add_job(hass.services.async_call(domain, SERVICE_TURN_OFF, data))
        elif domain == 'lock':
            if payload == mqtt_lock.DEFAULT_PAYLOAD_LOCK:
                hass.async_add_job(hass.services.async_call(domain, SERVICE_LOCK, data))
            if payload == mqtt_lock.DEFAULT_PAYLOAD_UNLOCK:
                hass.async_add_job(hass.services.async_call(domain, SERVICE_UNLOCK, data))
    
    async_track_state_change(hass, MATCH_ALL, _state_publisher)
    await mqtt.async_subscribe(hass, base_topic+'+/+/set', _state_message_received)
    return True