from rest_framework.serializers import ModelSerializer
from .models import Dato

class DatoSerializer(ModelSerializer):
    class Meta:
        model = Dato
        fields = '__all__'