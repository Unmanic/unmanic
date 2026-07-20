{{/*
Expand the name of the chart.
*/}}
{{- define "unmanic.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name (63 char limit).
*/}}
{{- define "unmanic.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Chart name and version for the chart label.
*/}}
{{- define "unmanic.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels.
*/}}
{{- define "unmanic.labels" -}}
helm.sh/chart: {{ include "unmanic.chart" . }}
{{ include "unmanic.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels.
*/}}
{{- define "unmanic.selectorLabels" -}}
app.kubernetes.io/name: {{ include "unmanic.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Service account name.
*/}}
{{- define "unmanic.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "unmanic.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
The port the Unmanic UI/API listens on. Follows config.ui_port when set so
the container port, service target, probes and NOTES all stay consistent.
*/}}
{{- define "unmanic.uiPort" -}}
{{- int (default 8888 (get .Values.config "ui_port")) -}}
{{- end }}

{{/*
The in-container cache path. Follows config.cache_path when set.
*/}}
{{- define "unmanic.cachePath" -}}
{{- default "/tmp/unmanic" (get .Values.config "cache_path") -}}
{{- end }}

{{/*
Probe scheme: HTTPS when in-app SSL is enabled (same port serves TLS).
*/}}
{{- define "unmanic.probeScheme" -}}
{{- ternary "HTTPS" "HTTP" .Values.ssl.enabled -}}
{{- end }}

{{/*
Checksum over everything that feeds the container environment, so config
changes roll the pod (ArgoCD-safe alternative to hooks). toJson emits maps
with sorted keys, keeping this deterministic.
*/}}
{{- define "unmanic.configChecksum" -}}
{{- dict
      "config" .Values.config
      "configSecret" .Values.configSecret
      "envFrom" .Values.envFrom
      "extraEnv" .Values.extraEnv
      "timezone" .Values.timezone
      "debugging" .Values.debugging
      "sqliteMaintenance" .Values.sqliteMaintenance
      "ssl" .Values.ssl
      "puid" .Values.puid
      "pgid" .Values.pgid
      "rootless" .Values.rootless
      "gpu" .Values.gpu
    | toJson | sha256sum -}}
{{- end }}
