node_id = data.get('node_id')
value_id = data.get('value_id')
delay = int(data.get('delay'))

service_data = { 'node_id': node_id, 'value_id': value_id }
time.sleep(delay)
hass.services.call('zwave', 'refresh_node_value', service_data, False)