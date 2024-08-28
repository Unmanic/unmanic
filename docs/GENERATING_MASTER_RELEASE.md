# Releasing staging into master

If you are only merging changes into `master` without performing a release, just run through steps 1 and 2.

If you are just going to release what is currently in the master branch, then skip to [Step 3](#step-3).

## Step 1: Compare commit history
Compare the `staging` and `master` branch commit history:
https://github.com/Unmanic/unmanic/compare/master...staging


## Step 2: Rebase merge into master
Perform a rebase merge from `staging` into `master` on the checked out repo. Push this change to the official repo's `master` branch.

> [!IMPORTANT]  
> If you are going to generate a tagged release, cancel the `Build All Packages CI` GitHub action for this push. This will be run again once we generate the release in the steps below. If you are not generating a release, let this action run.


## Step 3: Compare commit history since last release
Compare the `master` branch commit history since the last release:
https://github.com/Unmanic/unmanic/compare/0.2.7...master

While here, draft a changelog for the next release.


## Step 4: Create a GitHub release
Create a release in GitHub with these rules.
- The release should target the `master` branch.
- The release should tag the target when created. Use the format: `X.X.X`
- The release header should follow this template:
    ```
    [RELEASE] vX.X.X
    ```
- The release body should follow this template:
    ```
    - [NOTE] Add release notes here.


    ## Service
    - [NEW] This is a new feature added to the main service.
        - This is a bullet point to the above mentioned feature. 
    - [FIX] This is a fix for the main service.
        - This is a bullet point to the above mentioned fix. 
    - [IMPR] This is an improvement to an existing feature in the main service.
        - This is a bullet point to the above mentioned improvement. 

    ## Plugin executor
    - [NEW] ...
    - [FIX] ...
    - [IMPR] ...

    ## Docker
    - [NEW] ...
    - [FIX] ...
    - [IMPR] ...

    ## Front-end
    - [NEW] ...
    - [FIX] ...
    - [IMPR] ...
    ```
