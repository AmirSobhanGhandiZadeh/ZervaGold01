"""Custom pagination classes."""

from typing import Any

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class DynamicPageNumberPagination(PageNumberPagination):
    """Pagination with dynamic page size support."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    page_query_param = "page"

    def get_paginated_response(self, data: Any) -> Response:
        """Return paginated response with metadata."""
        return Response(
            {
                "data": data,
                "pagination": {
                    "current_page": self.page.number,
                    "total_pages": self.page.paginator.num_pages,
                    "total_items": self.page.paginator.count,
                    "page_size": self.get_page_size(self.request),
                    "has_next": self.page.has_next(),
                    "has_previous": self.page.has_previous(),
                    "next_page": (
                        self.page.next_page_number() if self.page.has_next() else None
                    ),
                    "previous_page": (
                        self.page.previous_page_number()
                        if self.page.has_previous()
                        else None
                    ),
                },
            }
        )

    def get_page_size(self, request) -> int:
        """Get page size from query param or default."""
        try:
            page_size = request.query_params.get(
                self.page_size_query_param, str(self.page_size)
            )
            page_size = int(page_size)
            return min(max(page_size, 1), self.max_page_size)
        except (ValueError, TypeError):
            return self.page_size
