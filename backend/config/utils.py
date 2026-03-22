from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response


class UploadImageMixin:


    image_serializer_class = None
    image_relation_field = None

    def get_image_serializer_class(self):
        if self.image_serializer_class is None:
            raise NotImplementedError()
        return self.image_serializer_class

    def get_image_relation_field(self):
        """Переопределяемый метод для получения названия связи"""
        if self.image_relation_field is None:
            raise NotImplementedError()
        return self.image_relation_field

    @action(detail=True, methods=['post'], url_path='upload-image')
    def upload_image(self, request, pk=None):
        serializer_class = self.get_image_serializer_class()
        relation_field = self.get_image_relation_field()
        parent_object = self.get_object()

        serializer = serializer_class(data=request.data, context={'request': request})

        if serializer.is_valid():
            serializer.save(**{relation_field: parent_object})


            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
