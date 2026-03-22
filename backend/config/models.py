from django.db import models
import hashlib

class BaseImage(models.Model):
    '''Базовая модель для картинок, использующая дедубликацию'''
    class Meta:
        abstract = True

    telegram_file_id = models.CharField(max_length=255, null=True, blank=True)
    hash = models.CharField(max_length=64, null=True, db_index=True, blank=True)


    def save(self, *args, **kwargs):

        if not self.hash:
            hash = self._generate_hash(self.image)

            existing = self.__class__.objects.filter(hash=hash).first()
            if existing:
                self.image = existing.image
                self.telegram_file_id = existing.telegram_file_id
                self.hash = hash
            else:
                self.hash = hash


        super().save(*args, **kwargs)

    @staticmethod
    def _generate_hash(file):
        '''Генерирует MD5 хеш для картинки'''
        hasher = hashlib.md5()
        for chunk in file.chunks():
            hasher.update(chunk)
        return hasher.hexdigest()