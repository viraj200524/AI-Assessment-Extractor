# Next.js Frontend Containerfile
FROM node:20-alpine AS runner
WORKDIR /app

COPY package.json package-lock.json* pnpm-lock.yaml* ./
RUN npm install -g pnpm && (pnpm install || npm install)

COPY . .

ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=development
ENV HOSTNAME="0.0.0.0"
ENV PORT=3000

EXPOSE 3000

CMD ["pnpm", "exec", "next", "dev", "-H", "0.0.0.0"]
