#
# Copyright (c) 2008-2016 the Urho3D project.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

task default: %w[sysroot_update]

# Usage: NOT intended to be used manually
desc 'Update armhf-sysroot in the master branch'
task :sysroot_update do
  system 'sudo apt-get update -q -y && sudo apt-get install -q -y --no-install-recommends kpartx qemu binfmt-support qemu-user-static' or abort 'Failed to install dependencies'
  system 'git clone --depth=1 https://github.com/urho3d/armhf-sysroot.git' or abort 'Failed to clone existing sysroot'
  system 'wget https://cloud-images.ubuntu.com/$name/current/$name-server-cloudimg-armhf-root.tar.gz -O root.tar.gz' or abort 'Failed to download latest armhf root tarball'
  system 'echo Untarring... && sudo tar xf root.tar.gz -C armhf-sysroot && sudo chown -R $USER: armhf-sysroot && rm root.tar.gz' or abort 'Failed to untar armhf root tarball'
  system 'echo Installing... && cp /usr/bin/qemu-arm-static armhf-sysroot/usr/bin && for f in dev dev/pts dev/shm proc run sys; do sudo mount --bind /$f armhf-sysroot/$f; done && sudo chroot armhf-sysroot /bin/bash -c \'apt-get update && apt-get -q -y upgrade && apt-get -q -y install libgles{1,2}-mesa-dev libx11-dev libxcursor-dev libxext-dev libxi-dev libxinerama-dev libxrandr-dev libxrender-dev libxss-dev libxxf86vm-dev libasound2-dev libpulse-dev libdbus-1-dev libreadline6-dev libudev-dev\' && for f in dev/pts dev/shm dev proc run sys; do sudo umount armhf-sysroot/$f; done' or abort 'Failed to install prerequisite software packages in new sysroot'
  system 'sudo chown -R $USER: armhf-sysroot' or abort 'Failed to change file ownership'
  `find armhf-sysroot/usr/lib/arm-linux-gnueabihf -type l |xargs ls -l |grep ' /'`.split("\n").each { |l| link = / ([^ ]+) -> ([^ ]+)/.match l; system "ln -sf #{link[2].sub '/', '../../../'} #{link[1]}" } and system 'ln -sf ld-linux-armhf.so.3 armhf-sysroot/lib/ld-linux.so.3 && ln -sfr armhf-sysroot/usr/lib/arm-linux-gnueabihf/libGLESv1_CM.so armhf-sysroot/usr/lib/arm-linux-gnueabihf/libGLESv1_CM.so.1 && ln -sfr armhf-sysroot/usr/lib/arm-linux-gnueabihf/libGLESv2.so armhf-sysroot/usr/lib/arm-linux-gnueabihf/libGLESv2.so.2' or abort 'Failed to fix symbolic links'
  replaced_content = File.read('armhf-sysroot/README.md').gsub(/\(.*?\)/m, "(#{File.new('armhf-sysroot/usr').mtime.utc.to_s})") and File.open('armhf-sysroot/README.md', 'w') { |file| file.puts replaced_content }
  system "echo Committing... && cd armhf-sysroot && git config user.name '#{ENV['GIT_NAME']}' && git config user.email '#{ENV['GIT_EMAIL']}' && git remote set-url --push origin https://#{ENV['GH_TOKEN']}@github.com/urho3d/armhf-sysroot.git && git add -Af . && rm -rf * && git checkout -- README.md usr/include usr/lib lib && git add -A . && ( git commit -q -m \"Travis CI: armhf sysroot update at #{Time.now.utc}.\" || true) && git push -q >/dev/null 2>&1" or abort 'Failed to push new sysroot'
end
