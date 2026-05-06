{{- define "ares.name" -}}ares{{- end -}}
{{- define "ares.fullname" -}}{{ .Release.Name }}-ares{{- end -}}
{{- define "ares.labels" -}}
app.kubernetes.io/name: {{ include "ares.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}
{{- define "ares.secretName" -}}{{ .Values.secrets.existingSecret }}{{- end -}}
