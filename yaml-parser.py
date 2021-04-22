import yaml
import requests
import re

URL = 'http://developer.opto22.com/static/generated/manage-rest-api/manage-api-public.yaml'

data = requests.get(URL)

json = yaml.load(data.text, Loader=yaml.BaseLoader)

endpoints = json['paths']

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

for path in endpoints:
	function = 'public '
	requestType = ''

	# determine the http request type
	if 'delete' in endpoints[path]:
		requestType = 'delete'
	if 'get' in endpoints[path]:
		requestType = 'get'
	if 'put' in endpoints[path]:
		requestType = 'put'
	if 'post' in endpoints[path]:
		requestType = 'post'
	
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

	if 'parameters' in endpoints[path][requestType]:
		parameters = 'PyDictionary parameters) {\n'
		parametersExist = True
	else:
		parameters = ') {\n'

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
	if parametersExist:

		for param in endpoints[path][requestType]['parameters']:
			if 'description' in param:
				paramDescription += functionName + '.param.' + param['name'] + "=" + param['description'] + '\n'
	
	# return value description
	returnDescription = ''
	if len(returnedValue) > 0:
		returnDescription += functionName + '.returns=' + endpoints[path][requestType]['responses']['200']['description'] + '\n'

	properties += functionDescription + paramDescription + returnDescription + '\n\n'

# write to .properties file
f = open('AbstractScriptModule.properties', 'w+')
f.write(properties)
f.close()