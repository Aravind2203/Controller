from django.shortcuts import render,redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from .forms import *
import re
from .models import *
import json
# Create your views here.
def index(request):
    return render(request,'index.html')
def register(request):
    """
    Registration page which shows a form for the user to complete
    """
    registered = False
    if request.method == 'POST':
        user_form = UserForm(data=request.POST)
        if user_form.is_valid():
            user = user_form.save()
            user.set_password(user.password)
            if user_form.cleaned_data['is_developer']:
                user.developer.active = True
                
            if user_form.cleaned_data['is_provider']:
                user.provider.active = True
                # When a new provider is registered,
                # a new rabbitmq user should be added to the system
                
                # TODO: create hyperledger fabric user
            #if USE_FABRIC:
            #    r = fabric.invoke_new_monetary_account(user.username, '700')
            #    if 'jwt expired' in r.text or 'jwt malformed' in r.text or 'User was not found' in r.text:
            #        token = fabric.register_user()
            #        r = fabric.invoke_new_monetary_account(user.username, '700', token = token)
            user.save()
            user = authenticate(username=user_form.cleaned_data['username'], password=user_form.cleaned_data['password'])
            login(request, user)
            messages.success(request, "Successful Login")
            registered = True
            if user_form.cleaned_data['is_provider']:
                return render(request, 'providers_app/index.html')
        else:
            print(user_form.errors)

    else:
        user_form = UserForm()
    return render(request, 'profiles/registration.html',
                           {'user_form': user_form,
                            'registered': registered})

@csrf_exempt
def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(username=username, password=password)

        if user:
            if user.is_active:
                login(request, user)
                messages.success(request, "Successful Login")
                return HttpResponseRedirect(reverse('index'))
            else:
                # If account is not active:
                return HttpResponse("Your account is not active.")
        else:
            messages.error(request, "Invalid username or password")
            return render(request, 'login.html', {})

    else:
        # Nothing has been provided for username or password.
        return render(request, 'login.html', {})

def add_task_to_queue(request, task, username):
    print("adding")
    """
    Adds a given task to a given user's queue and returns the response
    :param request:
    :param task: A docker container link or 'Stop' message
    :param username: Username of the provider who is going to receive the task
    :return: result of running the docker container -> is None if the task is 'Stop'
    """
    client = RpcClient()
    print(client)
    task_dict = json.dumps(task)
    client.call("jobs", task_dict)
    response = client.response
    print(response)
    job = get_object_or_404(Job, pk=task['job'])
    # print(response)
    job.corr_id = client.corr_id
    job.response = response.decode("utf-8")
    # print("job.response ", job.response)
    job.save(update_fields=['corr_id', 'response'])
    if response is None:
        return
    return json.loads(response.decode("utf-8"))


def request_handler(request, service, start_time, run_async=False):
    
  

    job = Job.objects.create(provider=None, service=service, start_time=start_time)
    # job.start_time = start_time
    job.save()
    task_link = service.docker_container
    task = re.search(r"/docker/(.*)$", task_link).group(1)
    task_developer = service.developer.id

    

    task_dict = {'task': task, 'task_developer':task_developer, 'job':job.id}
    response = add_task_to_queue(request, task_dict, None)
    # total_time = response['pull_time'] + response['run_time']
    print("response from provider: ", response)
    job.refresh_from_db()
    job.pull_time = response['pull_time']
    job.run_time = response['run_time']
    job.total_time = response['total_time']
    
    job.finished = True
    job.save()
    providing_time = int(((job.ack_time - job.start_time)/timedelta(microseconds=1))/1000) # Providing time in milliseconds
    
    return response, None, providing_time, str(job.id)

def run_service(request, service_id):
    response = ''
    try:
        service = Services.objects.get(id=service_id)
        print(service)
        if service.active:
            print("here")
            temp_time = datetime.now(tz=timezone(TIME_ZONE))
            response, provider, providing_time, job_id = request_handler(request, service, temp_time)
            
            messages.success(request, "Successfully sent a request to '{}' service of '{}'".format(service.name,
                                                                                                   service.developer))
        else:
            messages.error(request, "This service is disabled")

    except :
        messages.error(request, "Incorrect service id")
        return render(request, 'final_response.html')

    return render(request, 'final_response.html',
                  {'result': response,
                   'providing_time': providing_time,
                   'pull_time': response['pull_time'],
                   'run_time': response['run_time'],
                   'total_time': response['total_time'],
                   'provider': provider, 
                   'job_id': job_id})

@login_required()
def user_services(request):
    """
    Shows all services owned by a user.
    """
    all_services = Services.objects.filter(developer=request.user.developer)

    return render(request, 'developers_app/user_services.html',
                  {'all_services': all_services,
                   'developer_id': request.user.developer.id})