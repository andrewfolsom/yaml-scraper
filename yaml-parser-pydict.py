import yaml
import requests
import re

URL = 'http://developer.opto22.com/static/generated/manage-rest-api/manage-api-public.yaml'

data = requests.get(URL)

json = yaml.load(data.text, Loader=yaml.BaseLoader)

endpoints = json['paths']
schemas = json['components']['schemas']

requestTypes = ['delete', 'get', 'put', 'post']
bullet = '#8226; '

code = ''
properties = ''

# abstractFunction = """
#     @Override
#     @ScriptFunction(docBundlePrefix = "AbstractScriptModule")
#     public {type}{list} {function}{type}{plural}{by}({parameterDef}) {

#         return {function}{type}{plural}{by}Impl({parameters});
#     }

#     protected abstract {type}{list} {function}{type}{plural}{by}Impl({parameterDef});
# """
# gatewayScriptFunction = """
#     public {type}{list} {function}{type}{plural}{by}({parameterDef});
# """
# gatewayScriptModuleFunction """
#     @Override
#     protected {type}{list} {function}{type}{plural}{by}Impl({parameterDef}) {
#         return api.{function}{type}{plural}{by}();
#     }
# """
# clientScriptModuleFunction """
#     @Override
#     protected {type}{list} {function}{type}{plural}{by}Impl({parameterDef}) {
#         return rpc.{function}{type}{plural}{by}();
#     }
# """
# apiFunction = """
#     public {type}{list} {function}{type}{plural}{by}({parameterDef}) {
#         return {function}("{type}s?" {queryString}, {type}{list}.class);
#     }
# """

def definitionBuilder(schemaName):
	schema = schemas[schemaName]

	# construct definition of schema
	definition = ''
	
	if 'allOf' in schema:
		schemaRef = schema['allOf'][0]['$ref'].remove("'", '').remove('#/components/schemas/', '')
		definition += definitionBuilder(schemaRef)
	if 'properties' in schema:
		properties = schema['properties']
		for prop in properties:
			if 'type' in properties[prop]:
				if properties[prop]['type'] == 'array':
					definition += bullet + prop + ': ' + properties[prop]['type']
					items = properties[prop]['items']
					if 'oneOf' in items:
						definition += ', one of:'
						for option in items['oneOf']:
							definition += ' ' + option['type'] + ','
						definition += '<br>'
					elif 'type' in items:
						definition += ', type: ' + items['type'] + '<br>'
					elif '$ref' in items:
						schemaRef = items['$ref'].replace("'", '')
						schemaRef = schemaRef.replace('#/components/schemas/', '')
						definition += ', type: ' + schemaRef + '<br><br>' + schemaRef + 'Definition: <br>' + definitionBuilder(schemaRef)
				else:
					definition += bullet + prop + ': ' + properties[prop]['type'] + '<br>'

			# definition += '\n'

	return definition


def moduleBuilder(requestType):
	function = 'public '

	# determine the return type of the function
	returnedValue = endpoints[path][requestType]['responses']['200']['content']
	returnType = ''
	if len(returnedValue) == 0:
		returnType = 'void '
	else:
		returnType = 'String '

	function += returnType

	# get the function name
	functionName = endpoints[path][requestType]['operationId']
	function += functionName + '('

	# get the function arguments
	parameters = ''
	parametersExist = False
	requesetBodyExists = False

	if 'parameters' in endpoints[path][requestType]:
		parameters = 'PyDictionary parameters) {\n'
		parametersExist = True
	else:
		parameters = ') {\n'

	if 'requestBody' in endpoints[path][requestType]:
		requesetBodyExists = True

	function += parameters

	# declare function body
	body = '\t'

	if returnType == 'String ':
		body += 'return '

	body += requestType + '('

	# substitute the parameters, if applicable
	parameterizedPath = '"' + path + '"'
	if parametersExist:
		for param in endpoints[path][requestType]['parameters']:
			toReplace = '{' + param['name'] + '}'
			replacement = '" + parameters.get(' + param['name'] + ') + "'
			parameterizedPath = parameterizedPath.replace(toReplace, replacement)

	body += parameterizedPath + ');\n}\n'

	function += body

	# assemble properties entry for function
	# starting with description of function
	functionDescription = ''
	if 'description' in endpoints[path][requestType]:
		functionDescription = functionName + ".desc=" + endpoints[path][requestType]['description'] + '\n'
	
	# add parameter descriptions
	paramDescription = ''
	requestBodyDescription = ''

	if requesetBodyExists:
		if "'application/json'" in endpoints[path][requestType]['requestBody']['content']:
			schemaRef = endpoints[path][requestType]['requestBody']['content']["'application/json'"]['schema']['$ref']
			schemaRef = schemaRef.remove("'", '').remove('#/components/schemas/', '')
			paramDescription += functionName + '.param.' + schemaRef + '=' + schemaRef + '<br><br>' + schemaRef + 'Definition: <br>' + definitionBuilder(schemaRef) + '\n'
	if parametersExist:
		paramDescription += functionName + '.param.parameters=A PyDictionary containing: <br>'
		for param in endpoints[path][requestType]['parameters']:
			if 'description' in param:
				paramDescription += bullet + param['name'] + ": " + param['description'] + ' <br>'
		paramDescription += '\n'
	
	# return value description
	returnDescription = ''
	if len(returnedValue) > 0:
		returnDescription += functionName + '.returns=' + endpoints[path][requestType]['responses']['200']['description'] + '\n'

	return functionDescription + paramDescription + returnDescription + '\n\n'


for path in endpoints:

	# determine which http request types are present
	for requestType in requestTypes:
		if requestType in endpoints[path]:
			properties += moduleBuilder(requestType)
	
	

# write to .properties file
f = open('AbstractScriptModule.properties', 'w+')
f.write(properties)
f.close()

# save schema descriptions to .txt file
# f = open('definitions.txt', 'w+')
# f.write(definitionBuilder(schemas))
# f.close()