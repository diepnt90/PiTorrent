FROM alpine:3.22
RUN apk add --no-cache samba
COPY smb.conf /etc/samba/smb.conf
COPY start-samba.sh /usr/local/bin/start-samba.sh
RUN chmod +x /usr/local/bin/start-samba.sh
EXPOSE 137/udp 138/udp 139 445
CMD ["/usr/local/bin/start-samba.sh"]
