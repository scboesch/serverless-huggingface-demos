import base64
import json
import os
import boto3
from botocore.exceptions import ClientError


def handler(event, context):
    
    def get_response(text, functionARN):
        lambda_client = boto3.client('lambda')
        try:
            # Parameters to invoke the other Lambda function
            response = lambda_client.invoke(
                FunctionName=functionARN,  
                InvocationType='RequestResponse',  # 'Event' for async, 'RequestResponse' for sync
                Payload=json.dumps({'text': text})
            )

            # Read and parse the response payload
            response_payload = response['Payload'].read().decode('utf-8')
            response_data = json.loads(response_payload)
            return {
                    'message': 'Invocation successful',
                    'responseFromLambda': response_data
                }
        except Exception as e:
            return {
                    'message': 'Error invoking the function',
                    'error': str(e)
        
                }
                
    html = """
        <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Simple Form Submission</title>
    </head>
    <body>
        <h1>Invoke the Lambda-hosted Hugging Face model</h1>
        <label for="inputText">Enter Text:</label>
        <input type="text" id="inputText" name="inputText">
        <button onclick="submitData()">Submit</button>
        <p id="responseText"></p>
    
        <script>
            function submitData() {
                const inputValue = document.getElementById('inputText').value;
                fetch('\', { // Change '/submit' to your actual server endpoint
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ text: inputValue })
                })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('responseText').innerText = 'Response: ' + JSON.stringify(data['responseFromLambda']['body']);
                })
                .catch((error) => {
                    console.error('Error:', error);
                });
            }
        </script>
    </body>
    </html>
        
        """
    
    http_method = event.get('httpMethod')
    
    if http_method == 'GET':
        return {"statusCode": 200,
                "headers": {"content-type": "text/html"},
                "body": html}
    elif http_method == 'POST':
        body = json.loads(event['body'])
        text = body['text']
        functionARN = os.getenv("functionARN1")
        if "functionARN" in body:
            functionARN = body['functionARN']
    
        result = get_response(text, functionARN)
        return {"statusCode": 200,
            "headers": {"content-type": "text/html"},
            "body": json.dumps(result)}
    else:    
        return {"statusCode": 200,
                "headers": {"content-type": "text/html"},
                "body": "Invalid HTTP Method"}
