# Developer guide

This is a guide for developing on this repository and this library. For
instructions on how to _use_ `signalfx-python`, please refer to the
README.md file.

## Making a release

1. Figure out the next release version number (X.Y.Z) and update
   `signalfx/version.py`
1. Update the `CHANGELOG.md` file with information about the new
   release
1. Confirm the build and tests pass:
   ```
   tox
   ```
1. Commit and tag the release as vX.Y.Z:
   ```
   git add signalfx/version.py CHANGELOG.md
   git commit -m "Version X.Y.Z"
   git tag -s -m "Version X.Y.Z" vX.Y.Z HEAD
   ```
1. Build the release:
   ```
   python setup.py sdist bdist_wheel
   ```
1. Upload the release:
   ```
   twine upload dist/signalfx-X.Y.Z*
   ```
