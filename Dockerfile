FROM public.ecr.aws/lambda/python:3.13

WORKDIR /var/task

COPY requirements/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY src/ .

CMD ["src.main.ai_response_generator.lambda_handler"]