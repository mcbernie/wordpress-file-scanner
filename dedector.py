#!/usr/bin/python
#  ______________________________________________
# |                                              |
# | Wordpress file manipulation dedector (v0.1a) |
# |______________________________________________|
#
# My idea and how it (should) work:
# dedect local wordpress installation for file changes
# 1. download local wordpress version from wordpress.org
# 2. download all local installed wordpress plugins,  (if they downloadable)
# 3. make file comparson between original and installed files
# 4. mark all "only local files"
# 5. mark all "changed files" and run diff over it
# 6. generate simple html report
#
# Copyright (C) 2016  Nicolas Brueggemann(github:mcbernie)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os, re, sys, getopt
import urllib2, zipfile, shutil, filecmp, difflib, datetime, cgi
import Cheetah
from Cheetah.Template import Template

wordpress_path = ""
report_output = ""

print "= Wordpress file manipulation dedector"
print "= Version 0.01a mcbernie"
print "= License: GNU AGPLv3"
print "= updated at: 2016-05-19\n"

try:
    opts, args = getopt.getopt(sys.argv[1:], "hw:r:", ["wordpress=", "report="])
except getopt.GetoptError:
    print 'dedector.py -w <infectedwordpressinstallation> -r <path for html output>'
    sys.exit(2)
for opt, arg in opts:
    if opt == '-h':
        print ""
        print 'dedector.py -w <infectedwordpressinstallation> -r <path for html output>'
        sys.exit()
    elif opt in("-w", "--wordpress"):
        wordpress_path = arg
    elif opt in("-r", "--report"):
        report_output = arg

if wordpress_path == "" or not os.path.exists(wordpress_path):
    print "wordpress installation not exists"
    sys.exit(2)

plugins_path = os.path.join(wordpress_path, "wp-content", "plugins")

# folder for Downloads and Templates
home = os.path.expanduser("~")
temp_path = home +"/.wp_dedector"

downloading_enabled = True

## Init
if not os.path.exists(temp_path):
    os.makedirs(temp_path)
else:
    if downloading_enabled == True:
        shutil.rmtree(temp_path)
        os.makedirs(temp_path)
all_only_local_files = []
all_files_to_compare = []

class DownloadPluginInformations:
    def __init__(self, plugin, prepend_log = ""):
        self.plugin = plugin
        self.local_filename = self.plugin.name + "." + self.plugin.plugin_version + ".zip"
        self.downloaded = False
        self.extracted = False
        self.prepend_log = prepend_log

        #https://wordpress.org/plugins/akismet/
        #https://downloads.wordpress.org/plugin/akismet.3.1.11.zip
        #https://www.themepunch.com/revslider-doc/update-history/

    def download(self):
        if downloading_enabled == False:
            if os.path.exists(os.path.join(temp_path, self.plugin_name)):
                self.downloaded = True
                self.extracted = True
            return

        url = 'https://downloads.wordpress.org/plugin/' + self.plugin.name + "." + self.plugin.plugin_version + ".zip"

        if "twitterbootstrap-shortcodes-ultimate" in self.plugin.plugin_url:
            url = self.plugin.plugin_url.replace("twitterbootstrap-shortcodes-ultimate", "twitters-bootstrap-shortcodes-ultimate") + "/archive/" + self.plugin.plugin_version + ".zip"
        elif "github.com" in self.plugin.plugin_url:
            url = self.plugin.plugin_url + "/archive/v" + self.plugin.plugin_version + ".zip"

        request = urllib2.Request(url)
        try:
            response = urllib2.urlopen(request)
            with open(os.path.join(temp_path, self.local_filename), "wb") as local_file:
                local_file.write(response.read())
            self.downloaded = True
            with zipfile.ZipFile(os.path.join(temp_path,self.local_filename)) as zippedfile:
                for member in zippedfile.infolist():
                    words = member.filename.split('/')
                    path = temp_path + "/"
                    #for word in words[:-1]:
                    #    drive, word = os.path.split(word)
                    ##    head, word = os.path.split(word)
                    #    if word in (os.curdir, os.pardir, ''): continue
                    #    path = os.path.join(path, word)
                    zippedfile.extract(member, path)
            self.extracted = True
            os.remove(os.path.join(temp_path, self.local_filename))
        except urllib2.HTTPError, e:
            if e.code == 404:
                print self.prepend_log + " There is now Download for \"" + self.plugin.plugin_name + "\" "

class Plugin:
    def __init__(self, path, plugin_file, name):

        self.path = path
        self.plugin_file = plugin_file
        self.name = name
        self.plugin_name = ""
        self.plugin_url = ""
        self.plugin_version = ""
        self.set_values = False
        self.p_name_found = False
        self.p_uri_found = False
        self.p_ver_found = False
        self.infos()
        self.local_only = []
        self.pl_download = DownloadPluginInformations(self, prepend_log = "["+ self.plugin_name +"] ")

    def compare(self):
        #self.name + "." + self.plugin_version
        if self.pl_download.downloaded and self.pl_download.extracted:
            path = os.path.join(temp_path,self.name)
            if not os.path.isdir(path):
                if os.path.isdir(os.path.join(temp_path,self.name + "-" + self.plugin_version)):
                    path = os.path.join(temp_path,self.name + "-" + self.plugin_version)
            c = CompareFolder(local_installation=self.path, remote_installation=path, prepend_log = "["+ self.plugin_name +"] ")
            c.compare()
            self.local_only = c.local_onlys
        else:
            print "["+ self.plugin_name +"] nothing to compare. download:" + ( "yes" if self.pl_download.downloaded else "no") + " Extracting: " + ( "yes" if self.pl_download.extracted else "no")

    def print_info(self):
        print "["+ self.plugin_name +"] Path: " + self.path + ", Version: " + self.plugin_version + ", URL: " + self.plugin_url + " (Downloaded: " + ( "yes" if self.pl_download.downloaded else "no") + ", Extracted: " + ( "yes" if self.pl_download.extracted else "no") + ")"

    def download(self):
        if self.p_name_found == True and self.p_uri_found == True and self.p_ver_found == True:
            #print "["+ self.plugin_name +"] Start Downloading and Collection of Plugin informations for " + self.plugin_name
            self.pl_download.download()
        else:
            print "["+ self.plugin_name +"] cannot download data for \"" + self.plugin_name + "\" not enough data collected!"


    def infos(self):
        f = open(os.path.join(self.path,self.plugin_file), "r")

        for line in f:
            if "Plugin Name:" in line and self.p_name_found != True:
                self.plugin_name = line.split(": ")[1].strip()
                self.set_values = True
                self.p_name_found = True
            if "Plugin URI:" in line and self.p_uri_found != True:
                self.plugin_url = line.split(": ")[1].strip()
                self.set_values = True
                self.p_uri_found = True
            if "Version: " in line and self.p_ver_found != True:
                self.plugin_version = line.split(": ")[1].strip()
                self.set_values = True
                self.p_ver_found = True
            if self.p_ver_found == True and self.p_uri_found == True and self.p_name_found == True:
                break


class CollectPlugins:
    def __init__(self, wp_path):
        self.wp_path = wp_path
        self.plugin_path = os.path.join(wp_path, "wp-content", "plugins")
        self.list = []

    def find_main_file(self, path, search):
        #print "Search for "  + path + " with search " + search
        return os.path.isfile(os.path.join(path,search))

    def get_plugin(self, path_name, full_path):
        plugin_index_php = ""
        if self.find_main_file(full_path, path_name + ".php"):
            plugin_index_php = path_name + ".php"
        elif self.find_main_file(full_path, "wp-" + path_name + ".php"):
            plugin_index_php = "wp-" + path_name + ".php"
        elif self.find_main_file(full_path, "index.php"):
            plugin_index_php = "index.php"
        elif self.find_main_file(full_path, path_name.replace('-', '_') + ".php"):
            plugin_index_php = path_name.replace('-', '_') + ".php"
        elif self.find_main_file(full_path, path_name.replace('wp-', 'wordpress_').replace('-', '_') + "_js.php"):
            plugin_index_php = path_name.replace('wp-', 'wordpress_').replace('-', '_') + "_js.php"
        elif path_name == "wp-super-cache":
            plugin_index_php = "wp-cache.php"

        #print "Path: " + full_path + " plugin_indeX_php:" + plugin_index_php
        plugin = Plugin(full_path, plugin_index_php, path_name)
        self.list.append(plugin)

    def search_plugins(self):
        print "[Main > Plugins] Collect all installed plugins"
        self.list = []
        for child in os.listdir(self.plugin_path):
            full_plugin_path = os.path.join(self.plugin_path, child)
            if os.path.isdir(full_plugin_path):
                self.get_plugin(child, full_plugin_path)
        return self.list

class CompareFolder:
    def __init__(self, local_installation, remote_installation,ignore_plugins = False, ignore_uploads = False, ignore_themes = False, prepend_log = ""):
        self.local_installation = local_installation
        self.remote_installation = remote_installation
        self.i_plugins = ignore_plugins
        self.i_uploads = ignore_uploads
        self.i_themes = ignore_themes
        self.prepend_log = prepend_log
        self.local_onlys = []

    def onlys(self, dc, path, rp):

        onlyleft_folder = []
        onlyleft_files = []
        if dc:
            #print "Common Files: ", dc.common_files
            for f in dc.common_files:
                all_files_to_compare.append([os.path.join(path, f), os.path.join(rp, f)])

            for f in dc.left_only:
                if os.path.isdir(os.path.join(path,f)):
                    onlyleft_folder.append(f)
                    self.local_onlys.append(os.path.join(path,f))
                else:
                    onlyleft_files.append(f)
                    all_only_local_files.append(os.path.join(path,f))
                    self.local_onlys.append(os.path.join(path,f))

            if len(onlyleft_folder) > 0:
                print self.prepend_log + "following folders in \"" + path + "\" are only local: ", onlyleft_folder
            if len(onlyleft_files) > 0:
                print self.prepend_log + "following files in \"" + path + "\" are only local:   ", onlyleft_files

    def second_compare(self, lp, rp):
        dc = filecmp.dircmp(lp, rp,ignore=['.DS_Store', 'google*.html'])
        self.onlys(dc, lp, rp)

        for folder in dc.common_dirs:
            if os.path.join(self.local_installation,"wp-content","themes") in os.path.join(lp,folder) and self.i_themes:
                continue
            if os.path.join(self.local_installation, "wp-content","plugins") in os.path.join(lp,folder) and self.i_plugins:
                continue
            if os.path.join(self.local_installation, "wp-content","uploads") in os.path.join(lp,folder) and self.i_uploads:
                continue

            ext_dc = self.second_compare(os.path.join(lp,folder), os.path.join(rp,folder))
            self.onlys(ext_dc, os.path.join(lp,folder), os.path.join(rp,folder))

    def compare(self):
        self.second_compare(self.local_installation, self.remote_installation)

class WordpressChecker:
    def __init__(self, wordpress_path):
        self.path = wordpress_path
        self.installed_version = ""
        self.downloaded = False
        self.extracted = False

        self.read_version()
        print "[Main] Local Wordpress Version: " + self.installed_version
        self.download()
        self.plugins = CollectPlugins(self.path)
        self.plugins.search_plugins()

        c = CompareFolder(local_installation=self.path, remote_installation=os.path.join(temp_path,"wordpress"), ignore_uploads = True, ignore_themes = True, ignore_plugins = True, prepend_log = "[Main] ")
        c.compare()


    def read_version(self):
        f = open(os.path.join(self.path,"wp-includes", "version.php"), "r")
        for line in f:
            if "$wp_version = '" in line:
                self.installed_version = line.split('=')[1].replace("'", "").replace(";", "").strip()
                break

    def download(self):
        if downloading_enabled == False:
            self.downloaded = True
            self.extracted = True
            return
        #https://wordpress.org/latest.zip #https://wordpress.org/wordpress-4.5.2.zip
        sys.stdout.write("\r[Main] Start Downloading Wordpress Version...")
        sys.stdout.flush()
        local_filename = "wordpress-" + self.installed_version + ".zip"
        url = "https://wordpress.org/wordpress-" + self.installed_version + ".zip"
        request = urllib2.Request(url)
        try:
            response = urllib2.urlopen(request)
            with open(os.path.join(temp_path,local_filename), "wb") as local_file:
                local_file.write(response.read())
            self.downloaded = True
            sys.stdout.write("\r[Main] start extracting wordpress installation...")
            sys.stdout.flush()
            with zipfile.ZipFile(os.path.join(temp_path,local_filename)) as zippedfile:
                for member in zippedfile.infolist():
                    words = member.filename.split('/')
                    path = temp_path + "/"

                    zippedfile.extract(member, path)
            self.extracted = True
            os.remove(os.path.join(temp_path,local_filename))
            sys.stdout.write("\r[Main] wordpress version downloaded and extracted!\n")
            sys.stdout.flush()
        except urllib2.HTTPError, e:
            if e.code == 404:
                print "[Main] cannot download wordpress installation!"



wp_checker = WordpressChecker(wordpress_path)
print "[Main > Plugins] found ", len(wp_checker.plugins.list), " plugins ->"
template_plugins = []
for plugin in wp_checker.plugins.list:
    plugin.download()
    plugin.print_info()
    plugin.compare()
    template_plugins.append({
                            "info": "<b>" + plugin.plugin_name + "</b> Version:" + plugin.plugin_version,
                            "version": plugin.plugin_version,
                            "downloaded": plugin.pl_download.downloaded,
                            "localonly": plugin.local_only
                           })

print "\n"
for lfile in all_only_local_files:
    print "[Main > Localfile] only local file:" , lfile
print "\n"
print "[Main] make differ:"
diffcounter = 0

file_contents = []
not_the_same = []

for carr in all_files_to_compare:
    res = filecmp.cmp(carr[0],
                      carr[1],
                      shallow=True)

    if res == False:
        print "[Main > Comparing] " + carr[0] + " and " + carr[1] + " are not the Same!!"
        not_the_same.append("<u>" + carr[0] + "</u> <b>-</b> <u>" + carr[1] + "</u> Differ!")
        diff = difflib.ndiff(open(carr[0], "r").read().splitlines(), open(carr[1], "r").read().splitlines())
        a = "\n".join(diff)
        with open(os.path.join(temp_path, "differences_" + str(diffcounter) + ".diff"), "wb") as local_file:
            local_file.write(a)
        file_contents.append({"title": "differences between <span class='left'>"+carr[0]+"</span> and <span class='right'>"+carr[1]+"</span>",
                              "content": cgi.escape(a).replace("\n","<br/>"),
                              "file": os.path.join(temp_path,"/differences_" + str(diffcounter) + ".diff"),
                              "id": "differences_" + str(diffcounter)
                              })
        diffcounter += 1


t = Template(file=os.path.join("html_templates", "index.tmpl"))
t.local_installation_path = wp_checker.path
t.wordpress_version = wp_checker.installed_version
t.scanning_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
t.local_only = all_only_local_files
t.plugins_count = len(wp_checker.plugins.list)
t.plugins = template_plugins
t.files_to_compare_len = len(all_files_to_compare)
t.files_to_compare = not_the_same
t.local_only_files_len = len(all_only_local_files)

alof_array = []
id_count = 0
for alof in all_only_local_files:
    a = open(alof).read()
    alof_array.append({'title': alof,
                       'id': "local_only_file_" + str(id_count),
                       'content': cgi.escape(a).replace("\n","<br/>")})
    id_count += 1

t.local_only_files = alof_array
t.diff_files = file_contents

print "\n[Main > Report] Generating report.html"
with open(os.path.join(report_output, "report.html"), "wb") as local_file:
    local_file.write(str(t))

print "[Main > Cleanup] remove downloads and temp path"
shutil.rmtree(temp_path)
