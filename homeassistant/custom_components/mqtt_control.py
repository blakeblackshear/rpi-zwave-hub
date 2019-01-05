"""
Allow devices to be controlled as generic MQTT components.
"""
import json

import voluptuous as vol

from homeassistant.const import (CONF_DOMAINS, CONF_ENTITIES, CONF_EXCLUDE,
                                 CONF_INCLUDE, MATCH_ALL, SERVICE_TURN_ON, 
                                 SERVICE_TURN_OFF, ATTR_ENTITY_ID, SERVICE_LOCK,
                                 SERVICE_UNLOCK)
from homeassistant.components.zwave.const import (EVENT_NETWORK_COMPLETE, 
    EVENT_NETWORK_READY, EVENT_NETWORK_COMPLETE_SOME_DEAD)
from homeassistant.core import callback
from homeassistant.components import mqtt
from homeassistant.helpers.entityfilter import generate_filter
from homeassistant.helpers.event import async_track_state_change, async_call_later
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


def setup(hass, config):
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
    
    def _publish_all_states(*_):
        states = hass.states.all()
        for state in states:
            _state_publisher(state.entity_id, None, state)

    def _handle_hass_status(topic, payload, qos):
        if payload == 'online':
            async_call_later(hass, 20, _publish_all_states)

    def _state_publisher(entity_id, old_state, new_state):
        if new_state is None:
            return

        if not entity_filter(entity_id):
            return

        entity_id_parts = entity_id.split('.')
        domain = entity_id_parts[0]
        entity_state = hass.states.get(entity_id)

        mybase = base_topic + entity_id.replace('.', '/') + '/state'

        if domain == 'switch' or domain == 'binary_sensor':
            data = {}
            if new_state.state == 'on':
                data['state'] = 'ON'
            elif new_state.state == 'off':
                data['state'] = 'OFF'

            payload = json.dumps(data, cls=JSONEncoder)
            hass.components.mqtt.async_publish(mybase, payload, 1, False)
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
            hass.components.mqtt.async_publish(mybase, payload, 1, False)
        elif domain == 'lock':
            data = {}
            if new_state.state == 'locked':
                data['state'] = 'LOCK'
            elif new_state.state == 'unlocked':
                data['state'] = 'UNLOCK'
            
            try:
                data['notification'] = entity_state.attributes['notification']
            except KeyError:
                pass
            try:
                data['lock_status'] = entity_state.attributes['lock_status']
            except KeyError:
                pass

            payload = json.dumps(data, cls=JSONEncoder)
            hass.components.mqtt.async_publish(mybase, payload, 1, False)
        elif domain == 'sensor':
            data = {}
            data['state'] = new_state.state

            payload = json.dumps(data, cls=JSONEncoder)
            hass.components.mqtt.async_publish(mybase, payload, 1, False)

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
    mqtt.subscribe(hass, base_topic+'+/+/set', _state_message_received)
    mqtt.subscribe(hass, 'hass/status', _handle_hass_status)
    return True