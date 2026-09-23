FROM alpine:3.22
RUN apk add --no-cache samba
COPY smb.conf /etc/samba/smb.conf
EXPOSE 445
CMD ["smbd","--foreground","--no-process-group","--debug-stdout"]
