# HTTP Over MQTT

This goofy python script enables HTTP calls to made using MQTT as a proxy.
Why? If you have an IoT device with an unknown or private IP address with a HTTP/REST API, you can interface with it through a common MQTT broker.

## How To Run

This script is meant to be run as a service on the IoT device whose IP/whereabouts may be unknown.
In a posix environment, run the following from the directory where this script resides:
```bash
pip3 install -r requirements.txt # 'pip3' or 'pip', whichever
soure .env # Assuming your environment vars stored in .env
python3 server.py # 'python3' or 'python', whichever
```

## Usage

HTTP Over MQTT works by having one or multiple IoT devices connect to a remote MQTT broker and subscribe to a topic specific to their device.
The topic string will contain an HTTP verb and path, and the payload, if present, will contain query parameters, headers, and request body.
This service will then use the topic and payload to make an HTTP request to the configured API and return the response over a similar MQTT topic.

The device running HTTP Over MQTT will subscribe to `{app_name}/req/{id}/+/#` for requests and publish responses to `{app_name}/res/{id}/#`.
The values `{app_name}` and `{id}` are configurable via env vars `MQTT_TOPIC_START` and `MQTT_TOPIC_ID` (see Configuration).
These values can have slashes; leading and trailing slashes will be trimmed, so `///iot/config/v1////` will be interpreted as `iot/config/v1`

Given an `{app_name}` of `myapp/v1`, a unique device `{id}` of `L0L69`, and the device's base URL of `http://localhost:8000/rest/api/v1/` the device would subscribe to the remote broker on topic `myapp/v1/req/L0L69/+/#`. When a message arrives on topic `myapp/v1/req/L0L69/get/gps/latitude` with an empty payload, the device will make the call `GET http://localhost:8000/rest/api/v1/gps/latitude`, and if the device had a proper JSON API running at that endpoint, the device would send a message on topic `myapp/v1/res/L0L69/get/gps/latitude` with payload 
```json
{
    "content": {
        "latitude":38.88888
    },
    "status": 200,
    "req_id": null
}
```
If the response is JSON, `content` will be JSON. For anything else, like XML, HTML or plain text, `content` will be a string. `status` will be the HTTP status code, and `req_id` will be the same value sent with the request payload if one was provided, else null.
Notice that no payload was provided. All values in the payload optional. Payloads are JSON in the following format:
```json
{
    "params": <PARAMS>, # Flat dictionary of URL Query Parameters
    "body": <BODY>, # Body either JSON or a string
    "headers": <HEADERS>, # Flat dictionary of case-insensetive headers
    "req_id": <REQUEST_ID> # Value to be sent back with response; not impact on API call
}
```
If no path is provided in the message topic, i.e. topic ends with a verb (like `...../get`), the call will be made to the root of the configured base URL, as expected.

Building off of the previous example, a POST may look something like this:
A request message would arrive on topic `myapp/v1/req/L0L69/post/food/dessert` with payload
```json
{
    "body": {
        "dessertId": "applePie",
        "type": "pie"
        "notes": [
            "good with ice cream",
            "quintessentially American"
        ]
    },
    "req_id": "request_1337"
}
```
The device would make a call `POST http://localhost:8000/rest/api/v1/food/dessert` with the `application/json` body provided in the request, and the fictional API's response would be sent as a message on topic `myapp/v1/res/L0L69/post/food/dessert` with payload 
```json
{
    "content": "Yum. Resource created at /rest/api/v1/food/dessert/applePie",
    "status": 201,
    "req_id": "request_1337"
}
```

## Configuration

Copy `example.env` to anoth
er file, preferably `.env`, and edit the environment variables within.

| VAR NAME         | PURPOSE                                         | DEFAULT                                 |
|------------------|-------------------------------------------------|-----------------------------------------|
| MQTT_HOST        | Remote MQTT Broker hostname to connect to       | localhost # Should actually be remote   |
| MQTT_PORT        | Port to connect to Remote MQTT Broker on        | 8883 # Default for MQTTS (Secure MQTT)  |
| MQTT_USER        | MQTT Username                                   | # No default; anonymous connection      |
| MQTT_PASS        | MQTT Password                                   | # No default; anonymous connection      |
| MQTT_TOPIC_ID    | Portion of MQTT topic unique for each device    | itsme # Something like a serial number  |
| MQTT_TOPIC_START | Beginning portion of MQTT topic for application | v1 # For identifying application        |
| HTTP_BASE_URL    | Base URL for the device's API                   | http://localhost/ # Should be localhost |
| HTTP_USER        | Basic auth username for device's API            | # No default; leave blank if no auth    |
| HTTP_PASS        | Basic auth password for device's API            | # No default; leave blank if no auth    |

The HTTP configuration options allow only for Basic Auth, and are set on the device so that credentials aren't being sent back and forth over MQTT. A reasonable use case would be to have the API unautheticated and bound to localhost, allowing you to leave the HTTP_USER/PASS values blank. The MQTT_TOPIC_ID would be unique for each device, so device would only listening to requests destined for itself, and not the other one-thousand smart-fridges connected to the broker.

If you're actually going to use this for something important, take extreme to ensure your MQTT broker's ACL is configured properly so that not everyone connected to the broker can listen in and make their own requests at will.