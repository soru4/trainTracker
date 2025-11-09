import requests
import json
from django.http import JsonResponse, HttpResponseServerError
from google import genai
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.shortcuts import render
client = genai.Client(api_key=settings.GEMINI_API_KEY)

def home(request):

    return render(request, 'home.html')



def fetch_train_data(request):
  
    url = 'https://api-v3.amtraker.com/v3/trains'
    
    try:
        response = requests.get(url) 
        data = response.json()
        trains = []
        if isinstance(data, dict):
            for train_list in data.values():
                if isinstance(train_list, list):
                    trains.extend(train_list)
        return JsonResponse({'trains': trains})
  
    except Exception as e:
        print(f"An error occurred: {e}")
        return HttpResponseServerError("An error occurred.")


@csrf_exempt
@require_http_methods(["POST"])
def chat(request):
    try:
        body = json.loads(request.body)
        question = body.get('query', '').strip()
        if not question:
            return JsonResponse({'error': ''}, status=400)
        train_data_response = fetch_train_data(request)
        raw_trains_data = json.loads(train_data_response.content)['trains']
        
        simplifiedTrainData = []
        for train in raw_trains_data:
            simplifiedStations = []
            for s in train.get('stations', []) :
                if s.get('name'):
                    simplifiedStations.append(s.get('name'))
            route_name = train.get('routeName', 'Unknown Route')
            train_num = train.get('trainNum', 'No Number')
            if simplifiedStations:
                stations_list = ", ".join(simplifiedStations)
                train_string = (
                    f"Train {train_num} ({route_name}): Stops at {stations_list}"
                )
                simplifiedTrainData.append(train_string)

        if not simplifiedTrainData:
            answer = "No trains in the data currently."
            return JsonResponse({'answer': answer})

        trainDataPrompt = "\n".join(simplifiedTrainData)
        
        trainChatSetUP = (
            "You are a train chat. Answer questions about trains and stations based on the provided 'Train Data' to make inferences about train routes, stops, and schedules. If the answer is not contained within the 'Train Data', respond with 'I don't know'. Do not make up answers but make inferences. Do not include train numbers in responses."
             
        )
        prompt = (
            f"--- Train Data ({len(simplifiedTrainData)} Entries) ---\n {trainDataPrompt}\n \n\nUser Query: {question}\n\n Provide a concise answer based on the Train Data above:"
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={
                "system_instruction": trainChatSetUP,
                "max_output_tokens": 500,
                "temperature": 2.0, 
            }
        )
        
        if not response.text:
            print("Nothing was in the response")
            answer = "There is no train data available."
        else:
            answer = response.text.strip()
            
        return JsonResponse({'answer': answer})
    
    
    except Exception as e:
        print(f"Error: {e}")
        return HttpResponseServerError(f"An error occurred {e}")