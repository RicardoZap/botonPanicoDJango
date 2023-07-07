from django.db import models

# Create your models here.
class Dato(models.Model):
    unidad = models.TextField(max_length=50)
    device = models.TextField()
    primer_nombre = models.TextField()
    segundo_nombre = models.TextField(blank=True, default='')
    apellido_paterno = models.TextField()
    apellido_materno = models.TextField()
    numero_contacto = models.IntegerField(blank=True, default=0)
    notas = models.TextField(blank=True, default='')
    fecha_evento = models.TextField()

    def __str__(self):
        template = '{0.unidad} {0.device} {0.primer_nombre}'
        return template.format(self)
    

            
