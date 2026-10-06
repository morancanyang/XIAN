{{- define "xian.name" -}}xian{{- end -}}

{{- define "xian.labels" -}}
app.kubernetes.io/name: {{ include "xian.name" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{- define "xian.api.image" -}}
{{ .Values.image.registry }}/xian/api:{{ .Values.image.tag }}
{{- end -}}

{{- define "xian.worker.image" -}}
{{ .Values.image.registry }}/xian/worker:{{ .Values.image.tag }}
{{- end -}}

{{- define "xian.web.image" -}}
{{ .Values.image.registry }}/xian/web:{{ .Values.image.tag }}
{{- end -}}

{{- define "xian.env.common" -}}
- name: XIAN_ENV
  value: {{ .Values.env | quote }}
- name: XIAN_DB_DSN
  value: "postgresql+asyncpg://xian:$(POSTGRES_PASSWORD)@postgres:5432/xian"
- name: XIAN_REDIS_URL
  value: "redis://:$(REDIS_PASSWORD)@redis:6379/0"
- name: XIAN_CELERY_BROKER_URL
  value: "redis://:$(REDIS_PASSWORD)@redis:6379/1"
- name: XIAN_CLICKHOUSE_DSN
  value: "clickhouse://default:@clickhouse:8123/xian"
- name: XIAN_QDRANT_URL
  value: "http://qdrant:6333"
- name: XIAN_S3_ENDPOINT
  value: "http://minio:9000"
- name: POSTGRES_PASSWORD
  valueFrom:
    secretKeyRef: { name: xian-secrets, key: postgresPassword }
- name: REDIS_PASSWORD
  valueFrom:
    secretKeyRef: { name: xian-secrets, key: redisPassword }
- name: MINIO_PASSWORD
  valueFrom:
    secretKeyRef: { name: xian-secrets, key: minioPassword }
{{- end -}}