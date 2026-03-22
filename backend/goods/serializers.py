from rest_framework import serializers

from goods.models import GoodImage, Good


class GoodImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoodImage
        fields = ['id', 'image', 'is_invoice']
        read_only_fields = ['id']

    def validate(self, attrs):
        good = attrs.get('good') or (self.instance.good if self.instance else None)

        if good:

            queryset = good.images.all()

            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.count() >= 3:
                raise serializers.ValidationError(
                    "Для одного товара можно загрузить не более 3 фотографий."
                )
        return attrs


class GoodSerializer(serializers.ModelSerializer):

    images = GoodImageSerializer(many=True, read_only=True)

    class Meta:
        model = Good
        fields = [
            'id', 'quantity', 'title', 'images', 'label',
            'price', 'description', 'available',
        ]
        read_only_fields = ['id', ]


