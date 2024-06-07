import base64
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, JSONParser
from .models import UserSession
from langchain_openai import ChatOpenAI
from langchain.schema.messages import AIMessage, HumanMessage
from config.settings import OPENAI_API_KEY

chain = ChatOpenAI(model="gpt-4o", max_tokens=2048)

prompt="""You are a professional with specialized knowledge in the field of music.
Your role is to read the given sheet music and introduce the music to someone who has no background in music.
Refer to the following example to return results in Korean.
composer
Ludwig van Beethoven, the composer of this song, was born on December 16, 1770 in Bonn, Germany and died on March 26, 1827 in Vienna, Austria. He was a musician active during the transition from classicism to romanticism, and is considered one of the most important figures in music history.
background of the song It is known that Beethoven tried to express the pain and emotions caused by hearing loss through this song.

structure of the song
Adagio sostenuto: The very slow and calm first movement creates a soft and dreamy atmosphere, like moonlight reflected on a calm lake.
Allegretto: The second movement is a movement of a cheerful and bright character, with a short and concise form.
Presto agitato: The third and final movement is very fast and furious, demanding the pianist's technical ability.

characteristic
The Moonlight Sonata is a work that clearly demonstrates Beethoven's creativity and sensitivity, and is greatly loved among classical music lovers. This work is considered an important example of expanding the form and expressive possibilities of the piano sonata."""


def encode_image(upload_file):
    try:
        image_bytes = upload_file.read()
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        return base64_image
    except Exception as e:
        return None

def get_response(b64image, qsn):
    if not b64image:
        return {"error": "Image encoding failed."}

    msg = chain.invoke(
        [
            AIMessage(content=prompt),
            HumanMessage(content=[
                {"type": "text", "text": qsn},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64image, "detail": "auto"}}
            ])
        ]
    )
    return msg.content

class ChattingView(APIView):

    parser_classes = [MultiPartParser, JSONParser]

    def post(self, request):
        session_key = request.session.session_key or request.META.get('HTTP_SESSION_ID')
        if not session_key:
            request.session.create()
            session_key = request.session.session_key

        user_session, created = UserSession.objects.get_or_create(session_key=session_key)
        upload_image = request.data.get('image')
        qsn = request.data.get('question')

        if upload_image:
            # 처음 이미지를 업로드하는 경우 -> 기본 응답 반환
            b64_image = encode_image(upload_image)
            if b64_image:
                user_session.image_data = b64_image
                user_session.save()
                response = get_response(user_session.image_data, "")
                return Response({"response": response}, status=status.HTTP_200_OK)

            else:
                return Response({"error": "Image encoding failed."}, status=status.HTTP_400_BAD_REQUEST)

        if not upload_image and not user_session.image_data:
            return Response({"error": "No image available. Please upload an image first."},
                            status=status.HTTP_400_BAD_REQUEST)

        # 질문에 응답
        response = get_response(user_session.image_data, qsn)
        return Response({"response": response}, status=status.HTTP_200_OK)