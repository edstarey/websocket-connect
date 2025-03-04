FROM public.ecr.aws/lambda/python:3.13

WORKDIR /var/task

COPY requirements/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY src/ src/

CMD ["src.main.lambda_handler"]
