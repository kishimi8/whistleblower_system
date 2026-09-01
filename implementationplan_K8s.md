# Kubernetes (K8s) High Availability Deployment Plan

This document provides the complete architecture, Kubernetes manifest specifications, and operational workflows for deploying the Whistleblower System in a production-grade Kubernetes cluster.

---

## 1. Core Requirements & Architecture

### Key Requirements Addressed:
1. **Decoupled Databases across Separate Physical/Virtual Nodes**:
   - `whistle-db-primary` (PostgreSQL 15 Primary) and `whistle-db-standby` (PostgreSQL 15 Standby) are decoupled into distinct StatefulSets with separate dedicated PersistentVolumeClaims (PVCs).
   - Strict **Pod Anti-Affinity** (`topologyKey: kubernetes.io/hostname`) enforces that Primary and Standby pods are scheduled on **completely different Kubernetes worker nodes**.
2. **High-Availability Web Application Tier with Auto-Scaling**:
   - Initial deployment launches **2 web application pods** scheduled across separate worker nodes via Pod Anti-Affinity.
   - **Horizontal Pod Autoscaler (HPA v2)** dynamically scales the web tier between **2 and 10 pods** based on CPU (>70%) and Memory (>80%) utilization.
3. **Shared Evidence Storage**:
   - Persistent **ReadWriteMany (RWX)** volume mounted to `/code/media` across all autoscaling web pods, ensuring user-uploaded evidence is universally accessible.
4. **Zero-Race-Condition Database Migrations**:
   - Dedicated pre-deployment Kubernetes **Job** runs `manage.py migrate` and `collectstatic` prior to rolling out new application replica pods.

---

## 2. Cluster Topology & Node Distribution

```
                                [ Public Traffic ]
                                         │
                                ┌────────▼────────┐
                                │ Ingress Router  │ (TLS Termination)
                                └────────┬────────┘
                                         │
                                ┌────────▼────────┐
                                │ whistle-app-svc │ (ClusterIP: 8000)
                                └────────┬────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼ (Load-Balanced Across Nodes)                  ▼
        ┌──────────────────┐                            ┌──────────────────┐
        │  Worker Node 1   │                            │  Worker Node 2   │
        │                  │                            │                  │
        │ ┌──────────────┐ │    Pod Anti-Affinity (Node)│ ┌──────────────┐ │
        │ │ whistle-app  │◄├───────────────────────────►│ │ whistle-app  │ │
        │ │   (Pod 1)    │ │                            │ │   (Pod 2)    │ │
        │ └──────┬───────┘ │                            │ └──────┬───────┘ │
        │        │         │                            │        │         │
        │ ┌──────▼───────┐ │    Pod Anti-Affinity (Node)│ ┌──────▼───────┐ │
        │ │  db-primary  │◄├───────────────────────────►│ │  db-standby  │ │
        │ │  (Postgres)  │ │                            │ │  (Postgres)  │ │
        │ └──────┬───────┘ │                            │ └──────┬───────┘ │
        │        │         │                            │        │         │
        │ ┌──────▼───────┐ │                            │ ┌──────▼───────┐ │
        │ │ Primary PVC  │ │                            │ │ Standby PVC  │ │
        │ │ (Local RWO)  │ │                            │ │ (Local RWO)  │ │
        │ └──────────────┘ │                            │ └──────────────┘ │
        └──────────────────┘                            └──────────────────┘
                 │                                               │
                 └───────────────────────┬───────────────────────┘
                                         ▼
                           ┌───────────────────────────┐
                           │   Shared Media PVC (RWX)  │
                           │   (NFS / EFS / AzureFile) │
                           └───────────────────────────┘
```

---

## 3. Directory Layout for Manifests

```
whistleblower_system/
└── k8s/
    ├── 00-namespace.yaml              # Namespace definition
    ├── 01-secrets.yaml                # Database & Django credentials
    ├── 02-configmaps.yaml             # Postgres configs & initialization scripts
    ├── 03-storage.yaml                # PVCs (RWO for DBs, RWX for Media)
    ├── 04-db-primary.yaml             # Primary DB StatefulSet + Service (Node Anti-Affinity)
    ├── 05-db-standby.yaml             # Standby DB StatefulSet + Service (Node Anti-Affinity)
    ├── 06-redis.yaml                  # Redis Deployment + Service (Sessions & 2FA state)
    ├── 07-migration-job.yaml          # Pre-deployment migration & static collection Job
    ├── 08-app-deployment.yaml         # Django Web Deployment (2 replicas + Anti-Affinity) + Service
    ├── 09-hpa.yaml                    # Horizontal Pod Autoscaler (2 -> 10 replicas)
    ├── 10-ingress.yaml                # Ingress with TLS termination
    └── kustomization.yaml             # Kustomize manifest bundle
```

---

## 4. Kubernetes Manifest Specifications

### 1. `k8s/00-namespace.yaml`
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: whistleblower
  labels:
    app.kubernetes.io/name: whistleblower
```

---

### 2. `k8s/01-secrets.yaml`
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: whistle-secrets
  namespace: whistleblower
type: Opaque
stringData:
  DJANGO_SECRET_KEY: "change-this-to-a-secure-django-secret-key"
  DB_NAME: "whistle"
  DB_USER: "postgres"
  DB_PASSWORD: "secure_db_password"
  REPLICATION_USER: "replicator"
  REPLICATION_PASSWORD: "secure_replication_password"
  REDIS_PASSWORD: "secure_redis_password"
```

---

### 3. `k8s/02-configmaps.yaml`
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: whistle-db-config
  namespace: whistleblower
data:
  postgresql.conf: |
    listen_addresses = '*'
    port = 5432
    max_connections = 150
    shared_buffers = 256MB
    wal_level = replica
    max_wal_senders = 10
    max_replication_slots = 10
    wal_keep_size = 1024MB
    hot_standby = on
    archive_mode = on
    archive_command = '/bin/true'
    log_destination = 'stderr'

  init-primary.sh: |
    #!/bin/bash
    set -e
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        DO \$\$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${REPLICATION_USER:-replicator}') THEN
                CREATE ROLE ${REPLICATION_USER:-replicator} WITH REPLICATION LOGIN ENCRYPTED PASSWORD '${REPLICATION_PASSWORD}';
            END IF;
        END
        \$\$;
    EOSQL
    if ! grep -q "replication ${REPLICATION_USER:-replicator}" "$PGDATA/pg_hba.conf"; then
        echo "host replication ${REPLICATION_USER:-replicator} 0.0.0.0/0 md5" >> "$PGDATA/pg_hba.conf"
        echo "host all all 0.0.0.0/0 md5" >> "$PGDATA/pg_hba.conf"
    fi
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "SELECT pg_reload_conf();"

  entrypoint-standby.sh: |
    #!/bin/bash
    set -e
    PGDATA="${PGDATA:-/var/lib/postgresql/data}"
    PRIMARY_HOST="${PRIMARY_HOST:-whistle-db-primary-svc}"
    PRIMARY_PORT="${PRIMARY_PORT:-5432}"
    REPLICATION_USER="${REPLICATION_USER:-replicator}"

    until pg_isready -h "$PRIMARY_HOST" -p "$PRIMARY_PORT" -U "$POSTGRES_USER"; do
        echo "Waiting for primary database at ${PRIMARY_HOST}:${PRIMARY_PORT}..."
        sleep 2
    done

    if [ ! -s "$PGDATA/PG_VERSION" ]; then
        echo "Cloning primary with pg_basebackup..."
        rm -rf "${PGDATA:?}"/*
        PGPASSWORD="${REPLICATION_PASSWORD}" pg_basebackup \
            -h "$PRIMARY_HOST" \
            -p "$PRIMARY_PORT" \
            -U "$REPLICATION_USER" \
            -D "$PGDATA" \
            -Fp -Xs -R -v
        chmod 700 "$PGDATA"
    fi
    exec postgres -c hot_standby=on
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: whistle-app-config
  namespace: whistleblower
data:
  DEBUG: "False"
  ALLOWED_HOSTS: "whistle.finance.gov.ng,localhost,127.0.0.1,whistle-app-svc"
  CSRF_TRUSTED_ORIGINS: "https://whistle.finance.gov.ng,http://localhost"
  DB_HOST: "whistle-db-primary-svc"
  DB_PORT: "5432"
```

---

### 4. `k8s/03-storage.yaml`
```yaml
# Primary Database Dedicated Storage (RWO)
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: whistle-db-primary-pvc
  namespace: whistleblower
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
---
# Standby Database Dedicated Storage (RWO)
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: whistle-db-standby-pvc
  namespace: whistleblower
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
---
# Redis Persistent Volume (RWO)
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: whistle-redis-pvc
  namespace: whistleblower
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
---
# Shared Media Storage for Evidence Files (RWX - ReadWriteMany)
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: whistle-media-pvc
  namespace: whistleblower
spec:
  accessModes:
    - ReadWriteMany  # Requires NFS / AzureFile / AWS EFS storage class in multi-node
  resources:
    requests:
      storage: 1Gi
```

---

### 5. `k8s/04-db-primary.yaml` (Primary DB on Dedicated Node)
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: whistle-db-primary
  namespace: whistleblower
  labels:
    app.kubernetes.io/name: whistleblower
    app.kubernetes.io/component: database
    app.kubernetes.io/role: primary
spec:
  serviceName: whistle-db-primary-svc
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: whistleblower
      app.kubernetes.io/component: database
      app.kubernetes.io/role: primary
  template:
    metadata:
      labels:
        app.kubernetes.io/name: whistleblower
        app.kubernetes.io/component: database
        app.kubernetes.io/role: primary
    spec:
      affinity:
        # STRICT NODE ANTI-AFFINITY: Ensures Primary is NOT on the same node as Standby
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchExpressions:
                  - key: app.kubernetes.io/component
                    operator: In
                    values: ["database"]
              topologyKey: "kubernetes.io/hostname"
      containers:
        - name: postgres
          image: postgres:15-alpine
          command: ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf"]
          ports:
            - containerPort: 5432
              name: postgres
          env:
            - name: POSTGRES_DB
              valueFrom:
                secretKeyRef:
                  name: whistle-secrets
                  key: DB_NAME
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: whistle-secrets
                  key: DB_USER
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: whistle-secrets
                  key: DB_PASSWORD
            - name: REPLICATION_USER
              valueFrom:
                secretKeyRef:
                  name: whistle-secrets
                  key: REPLICATION_USER
            - name: REPLICATION_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: whistle-secrets
                  key: REPLICATION_PASSWORD
          resources:
            requests:
              cpu: "250m"
              memory: "512Mi"
            limits:
              cpu: "1000m"
              memory: "1536Mi"
          readinessProbe:
            exec:
              command: ["pg_isready", "-U", "postgres", "-p", "5432"]
            initialDelaySeconds: 5
            periodSeconds: 5
          livenessProbe:
            exec:
              command: ["pg_isready", "-U", "postgres", "-p", "5432"]
            initialDelaySeconds: 15
            periodSeconds: 10
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
            - name: config
              mountPath: /etc/postgresql/postgresql.conf
              subPath: postgresql.conf
            - name: init-scripts
              mountPath: /docker-entrypoint-initdb.d/init-primary.sh
              subPath: init-primary.sh
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: whistle-db-primary-pvc
        - name: config
          configMap:
            name: whistle-db-config
        - name: init-scripts
          configMap:
            name: whistle-db-config
            defaultMode: 0755
---
apiVersion: v1
kind: Service
metadata:
  name: whistle-db-primary-svc
  namespace: whistleblower
  labels:
    app.kubernetes.io/name: whistleblower
    app.kubernetes.io/component: database
    app.kubernetes.io/role: primary
spec:
  type: ClusterIP
  ports:
    - port: 5432
      targetPort: 5432
      name: postgres
  selector:
    app.kubernetes.io/name: whistleblower
    app.kubernetes.io/component: database
    app.kubernetes.io/role: primary
```

---

### 6. `k8s/05-db-standby.yaml` (Standby DB Decoupled on Node 2)
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: whistle-db-standby
  namespace: whistleblower
  labels:
    app.kubernetes.io/name: whistleblower
    app.kubernetes.io/component: database
    app.kubernetes.io/role: standby
spec:
  serviceName: whistle-db-standby-svc
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: whistleblower
      app.kubernetes.io/component: database
      app.kubernetes.io/role: standby
  template:
    metadata:
      labels:
        app.kubernetes.io/name: whistleblower
        app.kubernetes.io/component: database
        app.kubernetes.io/role: standby
    spec:
      affinity:
        # STRICT NODE ANTI-AFFINITY: Forces Standby onto a DIFFERENT worker node than Primary
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchExpressions:
                  - key: app.kubernetes.io/component
                    operator: In
                    values: ["database"]
              topologyKey: "kubernetes.io/hostname"
      containers:
        - name: postgres-standby
          image: postgres:15-alpine
          command: ["/entrypoint-standby.sh"]
          ports:
            - containerPort: 5432
              name: postgres
          env:
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: whistle-secrets
                  key: DB_USER
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: whistle-secrets
                  key: DB_PASSWORD
            - name: PRIMARY_HOST
              value: "whistle-db-primary-svc"
            - name: PRIMARY_PORT
              value: "5432"
            - name: REPLICATION_USER
              valueFrom:
                secretKeyRef:
                  name: whistle-secrets
                  key: REPLICATION_USER
            - name: REPLICATION_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: whistle-secrets
                  key: REPLICATION_PASSWORD
            - name: PGDATA
              value: "/var/lib/postgresql/data"
          resources:
            requests:
              cpu: "250m"
              memory: "512Mi"
            limits:
              cpu: "1000m"
              memory: "1536Mi"
          readinessProbe:
            exec:
              command: ["pg_isready", "-U", "postgres", "-p", "5432"]
            initialDelaySeconds: 10
            periodSeconds: 5
          livenessProbe:
            exec:
              command: ["pg_isready", "-U", "postgres", "-p", "5432"]
            initialDelaySeconds: 20
            periodSeconds: 10
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
            - name: entrypoint
              mountPath: /entrypoint-standby.sh
              subPath: entrypoint-standby.sh
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: whistle-db-standby-pvc
        - name: entrypoint
          configMap:
            name: whistle-db-config
            defaultMode: 0755
---
apiVersion: v1
kind: Service
metadata:
  name: whistle-db-standby-svc
  namespace: whistleblower
  labels:
    app.kubernetes.io/name: whistleblower
    app.kubernetes.io/component: database
    app.kubernetes.io/role: standby
spec:
  type: ClusterIP
  ports:
    - port: 5432
      targetPort: 5432
      name: postgres
  selector:
    app.kubernetes.io/name: whistleblower
    app.kubernetes.io/component: database
    app.kubernetes.io/role: standby
```

---

### 7. `k8s/06-redis.yaml`
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: whistle-redis
  namespace: whistleblower
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: whistleblower
      app.kubernetes.io/component: redis
  template:
    metadata:
      labels:
        app.kubernetes.io/name: whistleblower
        app.kubernetes.io/component: redis
    spec:
      containers:
        - name: redis
          image: redis:7-alpine
          command:
            - "redis-server"
            - "--appendonly"
            - "yes"
            - "--requirepass"
            - "$(REDIS_PASSWORD)"
          env:
            - name: REDIS_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: whistle-secrets
                  key: REDIS_PASSWORD
          ports:
            - containerPort: 6379
              name: redis
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          volumeMounts:
            - name: redis-storage
              mountPath: /data
      volumes:
        - name: redis-storage
          persistentVolumeClaim:
            claimName: whistle-redis-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: whistle-redis-svc
  namespace: whistleblower
spec:
  type: ClusterIP
  ports:
    - port: 6379
      targetPort: 6379
      name: redis
  selector:
    app.kubernetes.io/name: whistleblower
    app.kubernetes.io/component: redis
```

---

### 8. `k8s/07-migration-job.yaml`
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: whistle-migration-job
  namespace: whistleblower
spec:
  backoffLimit: 3
  template:
    metadata:
      labels:
        app.kubernetes.io/name: whistleblower
        app.kubernetes.io/component: migration
    spec:
      restartPolicy: OnFailure
      containers:
        - name: migration
          image: your-registry.azurecr.io/whistleblower-app:latest # Replace with your image
          command:
            - "sh"
            - "-c"
            - "python manage.py migrate --noinput && python manage.py collectstatic --noinput"
          envFrom:
            - configMapRef:
                name: whistle-app-config
          env:
            - name: SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: whistle-secrets
                  key: DJANGO_SECRET_KEY
            - name: DB_USER
              valueFrom:
                secretKeyRef:
                  name: whistle-secrets
                  key: DB_USER
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: whistle-secrets
                  key: DB_PASSWORD
            - name: REDIS_URL
              value: "redis://:$(REDIS_PASSWORD)@whistle-redis-svc:6379/1"
            - name: REDIS_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: whistle-secrets
                  key: REDIS_PASSWORD
          volumeMounts:
            - name: media-storage
              mountPath: /code/media
      volumes:
        - name: media-storage
          persistentVolumeClaim:
            claimName: whistle-media-pvc
```

---

### 9. `k8s/08-app-deployment.yaml` (2 Replicas on Separate Nodes + Service)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: whistle-app
  namespace: whistleblower
  labels:
    app.kubernetes.io/name: whistleblower
    app.kubernetes.io/component: web
spec:
  replicas: 2 # Initial 2 replicas
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app.kubernetes.io/name: whistleblower
      app.kubernetes.io/component: web
  template:
    metadata:
      labels:
        app.kubernetes.io/name: whistleblower
        app.kubernetes.io/component: web
    spec:
      affinity:
        # NODE SPREAD / ANTI-AFFINITY: Distributes the 2 web pods across separate worker nodes
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchExpressions:
                    - key: app.kubernetes.io/component
                      operator: In
                      values: ["web"]
                topologyKey: "kubernetes.io/hostname"
      containers:
        - name: web
          image: your-registry.azurecr.io/whistleblower-app:latest # Replace with your registry image
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8000
              name: http
          envFrom:
            - configMapRef:
                name: whistle-app-config
          env:
            - name: SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: whistle-secrets
                  key: DJANGO_SECRET_KEY
            - name: DB_USER
              valueFrom:
                secretKeyRef:
                  name: whistle-secrets
                  key: DB_USER
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: whistle-secrets
                  key: DB_PASSWORD
            - name: REDIS_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: whistle-secrets
                  key: REDIS_PASSWORD
            - name: REDIS_URL
              value: "redis://:$(REDIS_PASSWORD)@whistle-redis-svc:6379/1"
          resources:
            requests:
              cpu: "250m"
              memory: "512Mi"
            limits:
              cpu: "1000m"
              memory: "1Gi"
          readinessProbe:
            httpGet:
              path: /admin/login/
              port: 8000
            initialDelaySeconds: 15
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          livenessProbe:
            httpGet:
              path: /admin/login/
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 15
            timeoutSeconds: 5
            failureThreshold: 3
          volumeMounts:
            - name: media-storage
              mountPath: /code/media
      volumes:
        - name: media-storage
          persistentVolumeClaim:
            claimName: whistle-media-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: whistle-app-svc
  namespace: whistleblower
  labels:
    app.kubernetes.io/name: whistleblower
    app.kubernetes.io/component: web
spec:
  type: ClusterIP
  ports:
    - port: 8000
      targetPort: 8000
      name: http
  selector:
    app.kubernetes.io/name: whistleblower
    app.kubernetes.io/component: web
```

---

### 10. `k8s/09-hpa.yaml` (Autoscaler: 2 to 10 Replicas)
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: whistle-app-hpa
  namespace: whistleblower
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: whistle-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70 # Scale when avg CPU > 70%
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80 # Scale when avg Memory > 80%
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
        - type: Pods
          value: 2
          periodSeconds: 15
      selectPolicy: Max
    scaleDown:
      stabilizationWindowSeconds: 300 # 5 min stabilization window to prevent flapping
      policies:
        - type: Percent
          value: 25
          periodSeconds: 60
```

---

### 11. `k8s/10-ingress.yaml`
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: whistle-ingress
  namespace: whistleblower
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/proxy-body-size: "25m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
    - hosts:
        - whistle.finance.gov.ng
      secretName: whistle-tls-secret
  rules:
    - host: whistle.finance.gov.ng
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: whistle-app-svc
                port:
                  number: 8000
```

---

## 5. Deployment Execution Workflow

```bash
# 1. Build and push image to your container registry
docker build -f Dockerfile.app -t your-registry.azurecr.io/whistleblower-app:latest .
docker push your-registry.azurecr.io/whistleblower-app:latest

# 2. Apply Namespace and Configuration
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-secrets.yaml
kubectl apply -f k8s/02-configmaps.yaml
kubectl apply -f k8s/03-storage.yaml

# 3. Deploy Databases & Redis
kubectl apply -f k8s/04-db-primary.yaml
kubectl apply -f k8s/05-db-standby.yaml
kubectl apply -f k8s/06-redis.yaml

# 4. Wait for Primary DB to be Ready, then Run Migration Job
kubectl wait --for=condition=ready pod -l app.kubernetes.io/role=primary -n whistleblower --timeout=120s
kubectl apply -f k8s/07-migration-job.yaml
kubectl wait --for=condition=complete job/whistle-migration-job -n whistleblower --timeout=180s

# 5. Deploy Web App, HPA, and Ingress
kubectl apply -f k8s/08-app-deployment.yaml
kubectl apply -f k8s/09-hpa.yaml
kubectl apply -f k8s/10-ingress.yaml

# 6. Verify Node Separation & Scaling Status
kubectl get pods -n whistleblower -o wide
kubectl get hpa -n whistleblower
```
