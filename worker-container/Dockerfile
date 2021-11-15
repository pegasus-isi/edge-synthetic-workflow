FROM htcondor/execute:9.1-el7

RUN echo -e '#--     Authentication settings\n\
SEC_PASSWORD_FILE = /etc/condor/pool_password\n\
SEC_DEFAULT_AUTHENTICATION = REQUIRED\n\
SEC_DEFAULT_AUTHENTICATION_METHODS = FS,PASSWORD\n\
SEC_READ_AUTHENTICATION = OPTIONAL\n\
SEC_CLIENT_AUTHENTICATION = OPTIONAL\n\
SEC_ENABLE_MATCH_PASSWORD_AUTHENTICATION = TRUE\n\
DENY_WRITE = anonymous@*\n\
DENY_ADMINISTRATOR = anonymous@*\n\
DENY_DAEMON = anonymous@*\n\
DENY_NEGOTIATOR = anonymous@*\n\
DENY_CLIENT = anonymous@*\n'\
>> /root/config/custom.conf

ARG POOL_PASSWORD

RUN condor_store_cred -f /etc/condor/pool_password -p $POOL_PASSWORD

# set num slots to be a single slot
RUN printf "NUM_SLOTS = 1\nNUM_SLOTS_TYPE_1 = 1\nSLOT_TYPE_1 = 100%%\nSLOT_TYPE_1_PARTITIONABLE = false" \
    >> /root/config/custom.conf

RUN rm /etc/condor/config.d/01-pslots.conf

COPY ./entrypoint.sh /usr/bin/entrypoint.sh
RUN chmod +x /usr/bin/entrypoint.sh

ENTRYPOINT ["/usr/bin/entrypoint.sh"]
CMD ["/bin/bash", "-x", "/start.sh"]
