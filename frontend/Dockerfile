FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# T93 — Next.js inlines NEXT_PUBLIC_* vars into the client bundle at build
# time, not at container start, so a prebuilt image (as a real Helm/k8s
# install uses) needs this passed as --build-arg, not just a Deployment
# env var. docker-compose's dev setup avoids this because it runs `npm
# run build` at container start instead of at image-build time.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["npm", "start"]