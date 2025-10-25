from prefect.filesystems import GitHub

github_block = GitHub(
    repository="needa01/truecivic",  # your repo
    reference="main",               # always pull latest main branch
)
github_block.save("truecivic-repo", overwrite=True)

print("GitHub storage block 'truecivic-repo' created successfully!")
