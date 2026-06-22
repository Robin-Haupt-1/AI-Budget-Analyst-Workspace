"""SSE chat endpoint. Async view (served under ASGI) streaming agent output."""
import json

from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View

from .streaming import run_chat_stream


@method_decorator(csrf_exempt, name="dispatch")
class ChatView(View):
    async def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body.decode() or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "invalid JSON"}, status=400)

        scenario_id = body.get("scenario_id")
        message = (body.get("message") or "").strip()
        history = body.get("history") or []
        if not scenario_id or not message:
            return JsonResponse(
                {"error": "scenario_id and message are required"}, status=400
            )

        response = StreamingHttpResponse(
            run_chat_stream(int(scenario_id), message, history),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"  # disable proxy buffering for SSE
        return response
