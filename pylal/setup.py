# $Id$
# 
# setup for pylal

import os
from distutils.core import setup, Extension
from distutils.command import install
from distutils.command import sdist
from distutils import log
from sys import version_info
from numpy.lib.utils import get_include as numpy_get_include

class PkgConfig(object):
	def __init__(self, names):
		def stripfirsttwo(string):
			return string[2:]
		self.libs = map(stripfirsttwo, os.popen("pkg-config --libs-only-l %s" % names).read().split())
		self.libdirs = map(stripfirsttwo, os.popen("pkg-config --libs-only-L %s" % names).read().split())
		self.incdirs = map(stripfirsttwo, os.popen("pkg-config --cflags-only-I %s" % names).read().split())

full_lal_pkg_config = PkgConfig("lal lalframe lalmetaio lalsupport")
lal_pkg_config = PkgConfig("lal")

def remove_root(path,root):
  if root:
    return os.path.normpath(path).replace(os.path.normpath(root),"",1)
  else:
    return os.path.normpath(path)

class pylal_install(install.install):
  def run(self):

    # create the user env scripts
    if self.install_purelib == self.install_platlib:
      pylal_pythonpath = self.install_purelib
    else:
      pylal_pythonpath = self.install_platlib + ":" + self.install_purelib

    pylal_prefix = remove_root(self.prefix,self.root)
    pylal_install_scripts = remove_root(self.install_scripts,self.root)
    pylal_pythonpath = remove_root(pylal_pythonpath,self.root)
    pylal_install_platlib = remove_root(self.install_platlib,self.root)
    
    log.info("creating pylal-user-env.sh script")
    env_file = open(os.path.join('etc','pylal-user-env.sh'),'w')
    print >> env_file, "# Source this file to access PYLAL"
    print >> env_file, "PYLAL_PREFIX=" + pylal_prefix
    print >> env_file, "export PYLAL_PREFIX"
    print >> env_file, "PATH=" + pylal_install_scripts + ":${PATH}"
    print >> env_file, "PYTHONPATH=" + pylal_pythonpath + ":${PYTHONPATH}"
    print >> env_file, "LD_LIBRARY_PATH=" + pylal_install_platlib + ":${LD_LIBRARY_PATH}"
    print >> env_file, "DYLD_LIBRARY_PATH=" + pylal_install_platlib + ":${DYLD_LIBRARY_PATH}"
    print >> env_file, "export PATH PYTHONPATH LD_LIBRARY_PATH DYLD_LIBRARY_PATH"
    env_file.close()

    log.info("creating pylal-user-env.csh script")
    env_file = open(os.path.join('etc','pylal-user-env.csh'),'w')
    print >> env_file, "# Source this file to access PYLAL"
    print >> env_file, "setenv PYLAL_PREFIX " + pylal_prefix
    print >> env_file, "setenv PATH " + pylal_install_scripts + ":${PATH}"
    print >> env_file, "if ( $?PYTHONPATH ) then"
    print >> env_file, "  setenv PYTHONPATH " + pylal_pythonpath + ":${PYTHONPATH}"
    print >> env_file, "else"
    print >> env_file, "  setenv PYTHONPATH " + pylal_pythonpath
    print >> env_file, "endif"
    print >> env_file, "if ( $?LD_LIBRARY_PATH ) then"
    print >> env_file, "  setenv LD_LIBRARY_PATH " + pylal_install_platlib + ":${LD_LIBRARY_PATH}"
    print >> env_file, "else"
    print >> env_file, "  setenv LD_LIBRARY_PATH " + pylal_install_platlib
    print >> env_file, "endif"
    print >> env_file, "if ( $?DYLD_LIBRARY_PATH ) then"
    print >> env_file, "  setenv DYLD_LIBRARY_PATH " + pylal_install_platlib + ":${DYLD_LIBRARY_PATH}"
    print >> env_file, "else"
    print >> env_file, "  setenv DYLD_LIBRARY_PATH " + pylal_install_platlib
    print >> env_file, "endif"
    env_file.close()

    # now run the installer
    install.install.run(self)

class pylal_sdist(sdist.sdist):
  def run(self):
    # remove the automatically generated user env scripts
    for script in [ 'pylal-user-env.sh', 'pylal-user-env.csh' ]:
      log.info( 'removing ' + script )
      try:
        os.unlink(os.path.join('etc',script))
      except:
        pass

    # now run sdist
    sdist.sdist.run(self)


setup(
	name = "pylal",
	version = "0.1",
	author = "Patrick Brady",
	author_email = "patrick@gravity.phys.uwm.edu",
	description = "LSC Graphics Toolkit",
	url = "http://www.lsc-group.phys.uwm.edu/daswg/",
	license = "See file LICENSE",
	packages = ["pylal", "pylal.xlal"],
        cmdclass = { 'install' : pylal_install, 'sdist' : pylal_sdist },
	ext_modules = [
		Extension("pylal.support", ["src/support.c"],
			include_dirs = full_lal_pkg_config.incdirs,
			libraries = full_lal_pkg_config.libs,
			library_dirs = full_lal_pkg_config.libdirs,
			runtime_library_dirs = full_lal_pkg_config.libdirs),
                Extension("pylal.Fr", ["src/Fr.c"],
                        include_dirs = full_lal_pkg_config.incdirs + [numpy_get_include()],
			libraries = full_lal_pkg_config.libs,
			library_dirs = full_lal_pkg_config.libdirs,
			runtime_library_dirs = full_lal_pkg_config.libdirs),
		Extension("pylal.tools", ["src/tools.c"],
			include_dirs = lal_pkg_config.incdirs,
                        libraries = lal_pkg_config.libs,
                        library_dirs = lal_pkg_config.libdirs,
                        runtime_library_dirs = lal_pkg_config.libdirs),
		Extension("pylal.xlal.date", ["src/xlal/date.c"],
			include_dirs = lal_pkg_config.incdirs,
			libraries = lal_pkg_config.libs,
			library_dirs = lal_pkg_config.libdirs,
			runtime_library_dirs = lal_pkg_config.libdirs),
		Extension("pylal.xlal.inject", ["src/xlal/inject.c"],
			include_dirs = lal_pkg_config.incdirs + [numpy_get_include()],
			libraries = lal_pkg_config.libs,
			library_dirs = lal_pkg_config.libdirs,
			runtime_library_dirs = lal_pkg_config.libdirs)
	],
	scripts = [
                os.path.join("bin", "followup.py"),
	        os.path.join("bin", "plotbank"),
		os.path.join("bin", "plotbinj"),
		os.path.join("bin", "plotburca"),
		os.path.join("bin", "plotburst"),
		os.path.join("bin", "plotburstrate"),
		os.path.join("bin", "plotchannel"),
		os.path.join("bin", "plotdetresponse"),
		os.path.join("bin", "plotlalseries"),
		os.path.join("bin", "plotsiminspiral"),
		os.path.join("bin", "plotnumgalaxies"),
		os.path.join("bin", "upperlimit.py"),
		os.path.join("bin", "write_iul_page"),
		os.path.join("bin", "lalapps_compute_posterior"),
	        os.path.join("bin", "plotinjnum"),
		os.path.join("bin", "plotinspiral"),
		os.path.join("bin", "plotinspinj"),
		os.path.join("bin", "plotinspdiff"),
		os.path.join("bin", "plotinspmissed"),
		os.path.join("bin", "plotnumtemplates"),
		os.path.join("bin", "plotinspiralrange"),
		os.path.join("bin", "plotcoincseglength"),
		os.path.join("bin", "plotthinca"),
		os.path.join("bin", "plotethinca"),
		os.path.join("bin", "plotwindow"),
		os.path.join("bin", "plotcoincwindow"),
		os.path.join("bin", "ploteffdistcut"),
		os.path.join("bin", "plotefficiency"),
		os.path.join("bin", "plotsnrchi"),
		os.path.join("bin", "plotinsppop"),
		os.path.join("bin", "plottisi"),
		os.path.join("bin", "s3_statistic"),
		os.path.join("bin", "hipecoire"),
		os.path.join("bin", "lalapps_excesspowerfinal"),
		os.path.join("bin", "lalapps_ll2cache"),
		os.path.join("bin", "lalapps_path2cache"),
		os.path.join("bin", "lalapps_pire"),
		os.path.join("bin", "lalapps_stringfinal"),
		os.path.join("bin", "ligolw_binjfind"),
		os.path.join("bin", "ligolw_bucluster"),
		os.path.join("bin", "ligolw_bucut"),
		os.path.join("bin", "ligolw_burca"),
		os.path.join("bin", "ligolw_burca_tailor"),
		os.path.join("bin", "ligolw_cafe"),
		os.path.join("bin", "ligolw_segments"),
		os.path.join("bin", "ligolw_sschunk"),
		os.path.join("bin", "ligolw_sicluster"),
		os.path.join("bin", "ligolw_tisi")
	],
        data_files = [ ('etc',[
                os.path.join('etc','pylal-user-env.sh'),
                os.path.join('etc','pylal-user-env.csh')
        ] ) ]

)
