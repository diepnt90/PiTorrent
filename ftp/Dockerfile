FROM alpine:3.22
RUN apk add --no-cache vsftpd
COPY vsftpd.conf /etc/vsftpd/vsftpd.conf
EXPOSE 21 21100-21110
CMD ["vsftpd","/etc/vsftpd/vsftpd.conf"]
