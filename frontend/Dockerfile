FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Baked into the static bundle at build time — Vite env vars are not
# readable at container runtime, only at `vite build` time.
ARG VITE_API_BASE_URL=""
ARG VITE_VAPI_PUBLIC_KEY=""
ARG VITE_GOOGLE_CLIENT_ID=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_VAPI_PUBLIC_KEY=$VITE_VAPI_PUBLIC_KEY
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID

RUN npm run build

FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
