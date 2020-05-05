#! /bin/bash

# install gitlab-runner with `brew install gitlab-runner`

CMD="gitlab-runner exec docker \
    --docker-volumes /tmp/gitlab-runner/dist:/dist \
    --docker-volumes /tmp/gitlab-runner/builds:/builds:rw \
    --docker-volumes /tmp/gitlab-runner/cache:/cache:rw \
    ${@}"

echo "${CMD}"
bash -c "${CMD}"

