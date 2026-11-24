from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination


class SupportPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    @staticmethod
    def positive_integer(request, name, default, maximum=None):
        values = request.query_params.getlist(name)
        if not values:
            return default

        try:
            if len(values) != 1 or not (values[0].isascii() and values[0].isdecimal()):
                raise ValueError
            value = int(values[0])
            if value < 1 or (maximum is not None and value > maximum):
                raise ValueError
        except ValueError:
            message = (
                "Provide one positive integer."
                if maximum is None
                else f"Provide one integer from 1 to {maximum}."
            )
            raise ValidationError({name: [message]}) from None
        return value

    def get_page_size(self, request):
        return self.positive_integer(
            request, self.page_size_query_param, self.page_size, self.max_page_size
        )

    def get_page_number(self, request, paginator):
        return self.positive_integer(request, self.page_query_param, 1)

    def paginate_queryset(self, queryset, request, view=None):
        try:
            return super().paginate_queryset(queryset, request, view)
        except NotFound:
            raise ValidationError({"page": ["Page is out of range."]}) from None
