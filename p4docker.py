#####################################################
#          ___     _            _
#         /   |   | |          | |
#  _ __  / /| | __| | ___   ___| | _____ _ __
# | '_ \/ /_| |/ _` |/ _ \ / __| |/ / _ \ '__|
# | |_) \___  | (_| | (_) | (__|   <  __/ |
# | .__/    |_/\__,_|\___/ \___|_|\_\___|_|
# | |
# |_|
#####################################################
# Title:    p4docker
# Version:  2.1
# Author:   Jonas Werner
#####################################################

from flask import Flask, jsonify, request
import os
import docker
import json
from subprocess import Popen, PIPE


app = Flask(__name__)
client = docker.from_env()


# Docker command functions
################################################
# Get container status
def dockerContView():
    runningCont = {}
    cont = client.containers.list()

    # The container info is  buried inside the image object
    # With this we can dig it out for each container
    for entry in cont:
        name    = entry.__dict__['attrs']['Name']
        status  = entry.__dict__['attrs']['State']['Status']
        name = name.replace('/', '')
        runningCont[name] = status

    return runningCont

# Get info for public cloud containers
def cmdGetCont():

    contStatus = []

    process = Popen(['docker-machine', 'ls'], stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()

    stdout = stdout.decode() # stdout is in bytes format, decode to str
    lines = stdout.split('\n')

    for line in range(1, len(lines)-1):
        entries = lines[line].split() # Split on space

        print("Line: %s, Entries: %s" % (line, entries))

        contStatus.append(entries)

    return contStatus


# Get info for public cloud containers
def cmdStartCont(cont):
    cont = [cont] # Need to be passed to Popen as a list, not str
    process = Popen(['docker-machine', 'start'] + cont, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()


# Get names and number of docker images
def dockerImgView():
    contImageNames = {}
    contImages = client.images.list()

    # The container image names are buried inside the image object
    # With this we can dig it out for each container image
    for image in contImages:
        name    = image.__dict__['attrs']['RepoTags']
        id      = image.__dict__['attrs']['Id']

        # Only include containers with actual RepoTags
        if name:
            contImageNames[name[0]] = id

        # contImageNames.append(aaa)

    # print("Container names: %s" % contImageNames)
    return contImageNames


# Run containers
def dockerContRun(params):

    image   = params[0]
    name    = params[1]
    mode    = params[2]
    portInt = params[3]
    portExt = params[4]

    # The ports variable must be formatted as a dict
    ports = {}
    ports[portInt] = portExt

    # Maybe add a detach="True / false" value insteaD?
    if mode == "detached":
        contOutput = client.containers.run(image=image, ports=ports, name=name, detach=True)
    else:
        contOutput = client.containers.run(image=image, ports=ports, name=name)

    return contOutput.logs()


# REST API
#################################################

@app.route('/api/v1/docker/info',methods=['GET'])
def dockerInfo():
    req = request.args
    command = req['command']

    if command == "getImages":
        contImages = dockerImgView()
        returnData = json.dumps(contImages)
        code = 200

    elif command == "getCont":
        cont = dockerContView()
        returnData = cont
        code = 200

    elif command == "getPubCont":
        returnData = []
        tableValues = []
        contStatus = cmdGetCont()

        for i in range(0, len(contStatus)):
            tableValues = [contStatus[i][0],contStatus[i][2],contStatus[i][3]]
            returnData.append(tableValues)
        returnData = json.dumps(returnData)
        code = 200

    return returnData, code


@app.route('/api/v1/docker/run',methods=['GET'])
def dockerCreate():
    req = request.args
    params = []
    params.append(req['image'])
    params.append(req['name'])
    params.append(req['mode'])
    params.append(req['portInt'])
    params.append(req['portExt'])

    contOutput = dockerContRun(params)
    returnData = contOutput
    code = 201

    return returnData, code


@app.route('/api/v1/docker/stop',methods=['GET'])
def dockerDestroy():
    req = request.args
    cont = req['cont']

    if cont == "all":
        for container in client.containers.list():
          container.stop()

        contOutput = "All running containers have been stopped."
        returnCode = 201

    elif cont.isalnum():
        container = client.containers.get(cont)
        container.stop()
        contOutput = "Container with ID %s has been stopped." % cont
        returnCode = 201

    else:
        contOutput = "Invalid container ID or command provided. Plz try again."
        returnCode = 500

    returnData  = contOutput
    code        = returnCode

    return returnData, code

# def dockerStartPub():


@app.route('/api/v1/docker/start',methods=['GET'])
def dockerStart():
    req         = request.args
    cont        = req['cont']
    location    = req['location']

    if location == "public":
        cmdStartCont(cont)
        contOutput = "Container with ID %s has been started." % cont
        returnCode = 201

    elif location == "local":
        # container = client.containers.get(cont)
        # container.stop()
        contOutput = "Container with ID %s has been stopped." % cont
        returnCode = 201

    else:
        contOutput = "Invalid container ID or command provided. Plz try again."
        returnCode = 500

    returnData  = contOutput
    code        = returnCode

    return returnData, code



if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0', port=int(os.getenv('PORT', '5100')))
