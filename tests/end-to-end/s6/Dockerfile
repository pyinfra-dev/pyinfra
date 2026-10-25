# edge needed for s6-frontend
FROM alpine:edge

RUN apk add --no-cache -X http://dl-cdn.alpinelinux.org/alpine/edge/testing s6-overlay s6-frontend
RUN apk add --no-cache dbus polkit nix darkhttpd
# for debugging
RUN apk add --no-cache bash

RUN mkdir -p /var/lib/s6-rc/repository
RUN mkdir -p /etc/s6/sources
RUN echo "livedir=/run/s6-rc" >> /etc/s6.conf
#RUN printf >> /etc/s6.conf

RUN addgroup -S s6log
RUN adduser -S -H -D -G s6log -s /sbin/nologin s6log
ADD services/dbus-srv /etc/s6-overlay/s6-rc.d/dbus-srv
ADD services/dbus-log /etc/s6-overlay/s6-rc.d/dbus-log
ADD services/polkit-srv /etc/s6-overlay/s6-rc.d/polkit-srv
ADD services/polkit-log /etc/s6-overlay/s6-rc.d/polkit-log
ADD services/nix-daemon-srv /etc/s6-overlay/s6-rc.d/nix-daemon-srv
ADD services/nix-daemon-log /etc/s6-overlay/s6-rc.d/nix-daemon-log
ADD services/darkhttpd-srv /etc/s6-overlay/s6-rc.d/darkhttpd-srv
ADD services/darkhttpd-log /etc/s6-overlay/s6-rc.d/darkhttpd-log

RUN touch /etc/s6-overlay/user-bundles.d/user/contents.d/dbus
RUN touch /etc/s6-overlay/user-bundles.d/user/contents.d/polkit
# due to bug in s6-frontend, when no services are down, s6 live status exits 1, so have at least one
# service disabled
#RUN touch /etc/s6-overlay/user-bundles.d/user/contents.d/nix-daemon
#RUN touch /etc/s6-overlay/user-bundles.d/user/contents.d/darkhttpd

ENTRYPOINT ["/init"]
