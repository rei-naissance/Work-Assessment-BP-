FROM node:20-alpine

WORKDIR /app

COPY package.json .
RUN npm install

COPY . .

ARG VITE_API_PORT=7691
ENV VITE_API_PORT=$VITE_API_PORT
ENV PORT=7680

RUN npm run build

CMD ["npm", "run", "start"]
