'''
Parser for reading YAML files and turning them into .properties files
1. Iterate through the api endpoints
2. For each associated HTTP request, construct a description
	i. Descriptions consist of request description, parameter descriptions and a return description
	ii. If put or post, we need to check for a request body
3. Some descriptions reference schemas or borrow from their design
	i. We can construct these recursively by passing the name of the referenced schemas and using them as keys
'''

import yaml
import requests

def getYamlAsJson(url):
	data = requests.get(url)
	return yaml.load(data.text, Loader=yaml.BaseLoader)


def decapitalize(s):
	if not s:
		return s
	return s[0].lower() + s[1:]


def getNameFromReference(ref):
	name = ref.replace("'", '')
	name = name.replace('#/components/schemas/', '')
	return name


def getFunctionDescription(request):
	if 'description' in request:
		return request['operationId'] + '.desc=' + request['description'] + '\n'

	return ''


def getPropertyTypes(properties):
	schemaDef = ''

	for prop in properties:
		if 'type' in properties[prop]:
			propType = properties[prop]['type']
			if propType == 'array':
				schemaDef += bullet + prop + ': ' + propType
				items = properties[prop]['items']
				if 'oneOf' in items:
					options = [opt['type'] for opt in items['oneOf']]
					formatedOptions = ' || '.join(map(str, options)) + '<br>'
					schemaDef += ', one of ' + formatedOptions
				elif 'type' in items:
					schemaDef += ', type: ' + items['type'] + '<br>'
				elif '$ref' in items:
					schemaRef = items['$ref']
					schemaName = getNameFromReference(schemaRef)
					schemaDef += ', type: ' + schemaName + '<br><br>Type Definition:<br>' + schemaDefinition(schemas[schemaName])
			else:
				schemaDef += bullet + prop + ': ' + properties[prop]['type'] + '<br>'

		if 'anyOf' in properties[prop]:
			options = [opt['type'] for opt in properties[prop]['anyOf']]
			formatedOptions = ' || '.join(map(str, options)) + '<br>'
			schemaDef += bullet + prop + ": any of " + formatedOptions
		
		if '$ref' in properties[prop]:
			schemaRef = properties[prop]['$ref']
			schemaName = getNameFromReference(schemaRef)
			schemaDef += bullet + prop + '<br><br>Type Definition:<br>' + schemaDefinition(schemas[schemaName])

	return schemaDef


def schemaDefinition(schema):
	'''
	Property Construction Order of Operations:
	1. Does the description inherit from another schema? (Check for 'allOf')
		- If yes, pass the name of that schema to this function
		- Else, continue
	2. Does the description have properties?
		- If yes, check the property type:
			- If $ref, pass schema reference to this function
			- If array, check what array type:
				- If 'oneOf', list the data type options
				- If $ref, pass to this function
				- Else, just list the give data type
			- If basic data type, just list it
	'''

	schemaDef = ''

	# Check for inheritance
	if 'allOf' in schema:
		schemaRef = schema['allOf'][0]['$ref']
		schemaName = getNameFromReference(schemaRef)
		schemaDef += schemaDefinition(schemas[schemaName])

		if 'properties' in schema['allOf'][1]:
			properties = schema['allOf'][1]['properties']
			schemaDef += getPropertyTypes(properties)

		print(schemaDef)

		return schemaDef
		

	# Check for type
	if 'type' in schema:
		# Determine schema type
		schemaType = schema['type']

		if schemaType == 'object':

			# Check for other properties
			if 'properties' in schema:
				properties = schema['properties']
				schemaDef += getPropertyTypes(properties)

			return schemaDef

		if schemaType == 'array':
			schemaDef += bullet + schemaType
			items = schema['items']
			if 'oneOf' in items:
				schemaDef += ', one of:'
				for option in items['oneOf']:
					schemaDef += ' ' + option['type'] + ','
				schemaDef += '<br>'
			elif 'type' in items:
				schemaDef += ', type: ' + items['type'] + '<br>'
			elif '$ref' in items:
				schemaRef = items['$ref']
				schemaName = getNameFromReference(schemaRef)
				schemaDef += ', type: ' + schemaName + '<br><br>Type Definition:<br>' + schemaDefinition(schemas[schemaName])

			return schemaDef

		if schemaType == 'string':
			schemaDef += 'type: ' + schemaType
			
			if 'enum' in schema:
				enumOptions = ', '.join(map(str, schema['enum']))
				schemaDef += ', options: ' + enumOptions

			return schemaDef

	# If type not present, likely multipart/form data for a file
	for prop in schema['properties']:
		schemaDef += bullet + prop + ': ' + schema['properties'][prop]['format'] + ' ' + schema['properties'][prop]['type'] + '<br>'

	return schemaDef


def getParameterDescriptions(request):
	parameterDescriptions = ''

	# Check for parameters
	if 'parameters' in request:
		parameters = request['parameters']
		parameterDescriptions += request['operationId'] + '.param.parameters=A PyDictionary containing:<br>'
		for parameter in parameters:
			if 'description' in parameter:
				parameterDescriptions += bullet + parameter['name'] + ': ' + parameter['description'] + '<br>'

		parameterDescriptions += '\n'

	# Check for a request body
	if 'requestBody' in request:
		if 'application/json' in request['requestBody']['content']:
			schemaRef = request['requestBody']['content']['application/json']['schema']['$ref']
			schemaName = getNameFromReference(schemaRef)
			parameterDescriptions += request['operationId'] + '.param.' + decapitalize(schemaName) + '=' + schemaName + '<br><br>Type Definition<br>' + schemaDefinition(schemas[schemaName]) + '\n'

		if 'multipart/form-data' in request['requestBody']['content']:
			schema = request['requestBody']['content']['multipart/form-data']['schema']
			schemaName = schema['required'][0]
			parameterDescriptions += request['operationId'] + '.param.' + schemaName + '=' + schemaName.capitalize() + '<br><br>Type Definition<br>' + schemaDefinition(schema) + '\n'

	return parameterDescriptions


def getReturnDescription(request):
	responseDescription = ''
	responseContent = request['responses']['200']['content']

	if len(responseContent) > 0:
		responseDescription += request['operationId'] + '.returns=' + request['responses']['200']['description']

		if 'application/json' in responseContent:
			schema = responseContent['application/json']['schema']

			if '$ref' in schema:
				schemaName = getNameFromReference(schema['$ref'])
				responseDescription += '<br><br>Type Description:<br>' + schemaDefinition(schemas[schemaName]) + '\n\n'
				return responseDescription
			else:
				responseDescription += '<br><br>Type Description:<br>' + schemaDefinition(schema) + '\n\n'
				return responseDescription

		return responseDescription + '\n\n'

	return responseDescription + '\n'


def writeDescriptionsToFile(descriptions):
	f = open('AbstractScriptModule.properties', 'w+')
	f.write(descriptions)
	f.close


# Globals
json = getYamlAsJson('http://developer.opto22.com/static/generated/manage-rest-api/manage-api-public.yaml')
api = json['paths']
schemas = json['components']['schemas']
requestTypes = ['delete', 'get', 'put', 'post']
bullet = '&#8226; '

def main():
	descriptions = ''

	# Iterate over each endpoint
	for endpoint in api:

		# Check for implementations of each HTTP request type
		for requestType in requestTypes:
			if requestType in api[endpoint]:
				request = api[endpoint][requestType]

				# Add the function description
				descriptions += getFunctionDescription(request)

				# Add parameter descriptions
				descriptions += getParameterDescriptions(request)

				# Add return description
				descriptions += getReturnDescription(request)

	# Write descriptions to file
	writeDescriptionsToFile(descriptions)


main()