FROM alpine:3.22
RUN apk add --no-cache vsftpd
COPY vsftpd.conf /etc/vsftpd/vsftpd.conf
COPY start-ftp.sh /usr/local/bin/start-ftp.sh
RUN chmod +x /usr/local/bin/start-ftp.sh
EXPOSE 21 21100-21110
CMD ["/usr/local/bin/start-ftp.sh"]
