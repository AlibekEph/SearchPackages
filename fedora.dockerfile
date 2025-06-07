FROM fedora:43

LABEL Name=lab0
LABEL Version=1

ARG STUDENT=sueta
ENV STUDENT=$STUDENT

RUN dnf install --nodocs --setopt=install_weak_deps=False -y \
      sudo \
      util-linux \
      git \
      curl \
      vim \
      nano \
      python3 \
      python3-pip \
      python3-devel \
      koji \
      hwloc-libs \
      ncurses-libs \
      ncurses-compat-libs \
      libuuid \
      wget \
      rpm-build \
      make \
      gcc \
      gcc-c++ \
      clang \
    && rm -rf /var/cache /var/log/dnf* /var/log/yum.* \
    && dnf clean all

RUN groupadd -g 1000 $STUDENT \
 && useradd -ms /bin/bash -u 1000 -g $STUDENT $STUDENT

RUN mkdir -p ~/.koji \
 && printf '[koji]\nserver = https://koji.fedoraproject.org/kojihub\n' > ~/.koji/config

RUN echo "$STUDENT:$STUDENT" | chpasswd \
 && echo "$STUDENT ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/$STUDENT

RUN echo "alias ll='ls -alF'" | su $STUDENT -c "tee -a /home/$STUDENT/.bashrc"
RUN echo "alias la='ls -A'"  | su $STUDENT -c "tee -a /home/$STUDENT/.bashrc"
RUN echo "alias l='ls -CF'" | su $STUDENT -c "tee -a /home/$STUDENT/.bashrc"

USER $STUDENT
WORKDIR /home/$STUDENT/LAB0

COPY --chown=$STUDENT:$STUDENT requirements.txt ./
RUN sudo pip3 install --user --no-cache-dir -r requirements.txt

COPY --chown=$STUDENT:$STUDENT . .

EXPOSE 5000

#ENTRYPOINT [ "/bin/bash", "-lc", "python3 search_packages.py" ]

ENTRYPOINT [ "/bin/bash", "-lc", "tail -f /dev/null" ]
