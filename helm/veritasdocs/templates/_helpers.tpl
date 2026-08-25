{{- define "veritasdocs.fullname" -}}
{{ .Release.Name }}
{{- end -}}

{{- define "veritasdocs.labels" -}}
app.kubernetes.io/part-of: veritasdocs
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "veritasdocs.selectorLabels" -}}
app.kubernetes.io/part-of: veritasdocs
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "veritasdocs.image" -}}
{{- printf "%s%s:%s" .registry .repository .tag -}}
{{- end -}}

{{/*
Explicit env: list (not envFrom) for values that reference secret-backed
passwords via Kubernetes $(VAR) substitution — that expansion only sees
vars defined through `env:`, not `envFrom:`, so POSTGRES_URL/REDIS_URL
have to be built here rather than in the ConfigMap.
*/}}
{{- define "veritasdocs.appEnv" -}}
- name: POSTGRES_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "veritasdocs.fullname" . }}-secrets
      key: postgres-password
- name: POSTGRES_URL
  value: "postgresql+asyncpg://veritasdocs:$(POSTGRES_PASSWORD)@{{ include "veritasdocs.fullname" . }}-postgres:5432/veritasdocs"
- name: REDIS_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "veritasdocs.fullname" . }}-secrets
      key: redis-password
- name: REDIS_URL
  value: "redis://:$(REDIS_PASSWORD)@{{ include "veritasdocs.fullname" . }}-redis:6379/0"
- name: JWT_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "veritasdocs.fullname" . }}-secrets
      key: jwt-secret-key
- name: AWS_ACCESS_KEY_ID
  valueFrom:
    secretKeyRef:
      name: {{ include "veritasdocs.fullname" . }}-secrets
      key: s3-access-key-id
- name: AWS_SECRET_ACCESS_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "veritasdocs.fullname" . }}-secrets
      key: s3-secret-access-key
- name: OPENAI_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "veritasdocs.fullname" . }}-secrets
      key: openai-api-key
      optional: true
- name: ANTHROPIC_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "veritasdocs.fullname" . }}-secrets
      key: anthropic-api-key
      optional: true
- name: GROQ_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "veritasdocs.fullname" . }}-secrets
      key: groq-api-key
      optional: true
- name: GOOGLE_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "veritasdocs.fullname" . }}-secrets
      key: google-api-key
      optional: true
- name: COHERE_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "veritasdocs.fullname" . }}-secrets
      key: cohere-api-key
      optional: true
- name: LLAMAPARSE_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "veritasdocs.fullname" . }}-secrets
      key: llamaparse-api-key
      optional: true
{{- end -}}
