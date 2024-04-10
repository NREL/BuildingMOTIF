FROM node:18.10.0

WORKDIR /buildingmotif-app
COPY . .

RUN npm install -g @angular/cli
RUN npm install

CMD ng serve --host 0.0.0.0
