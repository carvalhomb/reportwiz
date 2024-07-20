FROM python:3.11
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app
COPY --chown=user ./ $HOME/app/
#RUN mkdir -p $HOME/app/.chainlit
#COPY -R --chown=user .chainlit/ $HOME/app/.chainlit
#RUN mkdir -p $HOME/app/data
#COPY -R --chown=user data/ $HOME/app/data
#RUN mkdir -p $HOME/app/public
#COPY --chown=user public/ $HOME/public
COPY ./requirements.txt ~/app/requirements.txt
RUN pip install -r requirements.txt
COPY . .
CMD ["chainlit", "run", "app.py", "--port", "7860"]