# Use an AWS Lambda base image for Python 3.10
FROM public.ecr.aws/lambda/python:3.10

# Copy the requirements file and install dependencies
COPY requirements/requirements.txt ${LAMBDA_TASK_ROOT}/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copy the entire project into the Lambda task root
COPY . ${LAMBDA_TASK_ROOT}

CMD ["app.main.handler"]