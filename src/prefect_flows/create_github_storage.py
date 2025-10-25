import asyncio
from prefect_github import GitHubRepository

async def main():
    github_block = GitHubRepository(
        repository_url="https://github.com/needa01/truecivic.git",
        reference="main",
    )
    await github_block.save("truecivic-repo", overwrite=True)
    print("GitHub storage block 'truecivic-repo' created successfully!")

asyncio.run(main())
