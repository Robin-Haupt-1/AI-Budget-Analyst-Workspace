FROM node:20-slim
WORKDIR /app
# Only the dependency manifests are baked in (so `npm install` is a cached image
# layer). The app source is bind-mounted via docker-compose for hot reload; the
# image's /app/node_modules is preserved by an anonymous volume so the host mount
# doesn't shadow it. `package*.json` also picks up a lockfile if one exists.
COPY package*.json ./
RUN npm install
EXPOSE 3000
# Dev server keeps the scaffold simple to run; switch to build+start for prod.
CMD ["npm", "run", "dev"]
