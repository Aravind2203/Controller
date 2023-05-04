from django import forms
from django.contrib.auth.models import User
from .models import *
import pika
import uuid
from django.conf import settings

class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())
    is_provider = forms.BooleanField(label="Do you want to be a provider?", required=False)
    is_developer = forms.BooleanField(label="Do you want to be a developer?", required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'password')


class ChangeInfoForm(forms.ModelForm):
    is_developer = forms.BooleanField(required=False)
    is_provider = forms.BooleanField(required=False)

    class Meta:
        model = User
        fields = ('username', 'email')

class ServiceForm(forms.ModelForm):
    class Meta:
        model = Services
        fields = ('name', 'docker_container')

class RpcClient(object):
    """
    This is the rabbitmq RpcClient class.
    """

    def __init__(self):
        print("client")
        credentials = pika.PlainCredentials("ohwbxpft","Qyp6xxRvgDEIX4VmBQQJgKKjWgihB3vU")
        self.connection = pika.BlockingConnection(
        pika.ConnectionParameters("armadillo.rmq.cloudamqp.com", 5672,"ohwbxpft", credentials=credentials))
        # if not settings.RABBITMQ_PORT:
        #     self.connection = pika.BlockingConnection(
        #         pika.ConnectionParameters(host=settings.RABBITMQ_HOST, credentials=credentials))
        # else:
        #     self.connection = pika.BlockingConnection(
        #         pika.ConnectionParameters(settings.RABBITMQ_HOST, settings.RABBITMQ_PORT, credentials=credentials))
        print(self.connection)
        self.channel = self.connection.channel()

        result = self.channel.queue_declare(queue='jobs')
        self.callback_queue = result.method.queue

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True)
        self.response = None

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, queue_name, request):
        print("here")
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=request)
        if request == '"Stop"':
            return
        while self.response is None:
            self.connection.process_data_events()
        return self.response