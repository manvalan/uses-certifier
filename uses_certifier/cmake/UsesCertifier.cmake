# UsesCertifier.cmake: verify the uses-certifier certificate on every build.
#
# Include it from the top-level CMakeLists.txt, after project():
#
#   execute_process(COMMAND uses-certifier cmake-module
#                   OUTPUT_VARIABLE USES_CERTIFIER_MODULE
#                   OUTPUT_STRIP_TRAILING_WHITESPACE
#                   COMMAND_ERROR_IS_FATAL ANY)
#   include(${USES_CERTIFIER_MODULE})
#   uses_certifier_check()
#
# uses_certifier_check() adds a target that runs `uses-certifier check` on
# every build, and makes every executable and library of the project
# depend on it: no target compiles until the sources match the committed
# certificate. Code that is not certified, is below the required level or
# changed after it was certified fails the build. It builds only when a
# person authorizes it in certification/authorizations.yaml (see
# `uses-certifier authorize`); every authorized file is printed on each
# build. There is no option to skip the check.
#
# Options (all optional):
#   TARGET name          name of the check target (uses_certification)
#   PROJECT_DIR dir      root of the certified project (the source dir)
#   CERTIFICATE file     certificate (the project's configured one)
#   AUTHORIZATIONS file  authorizations (the project's configured one)
#   MIN_LEVEL level      also require this level
#   GUARD targets...     guard only these targets instead of all of them
#
# Requires CMake 3.19 and uses-certifier on the PATH, or in the
# USES_CERTIFIER_EXECUTABLE cache variable.

cmake_minimum_required(VERSION 3.19)

include_guard(GLOBAL)

function(uses_certifier_check)
  cmake_parse_arguments(PARSE_ARGV 0 ARG ""
    "TARGET;PROJECT_DIR;CERTIFICATE;AUTHORIZATIONS;MIN_LEVEL" "GUARD")
  if(ARG_UNPARSED_ARGUMENTS)
    message(FATAL_ERROR
      "uses_certifier_check: unknown arguments ${ARG_UNPARSED_ARGUMENTS}")
  endif()
  if(NOT ARG_TARGET)
    set(ARG_TARGET uses_certification)
  endif()
  if(NOT ARG_PROJECT_DIR)
    set(ARG_PROJECT_DIR "${CMAKE_CURRENT_SOURCE_DIR}")
  endif()
  _uses_certifier_find()
  _uses_certifier_command(command)
  add_custom_target(${ARG_TARGET} ALL
    COMMAND ${command}
    WORKING_DIRECTORY "${ARG_PROJECT_DIR}"
    COMMENT "Checking code certification (uses-certifier)"
    VERBATIM)
  if(ARG_GUARD)
    _uses_certifier_guard(${ARG_TARGET} ${ARG_GUARD})
  else()
    cmake_language(EVAL CODE "
      cmake_language(DEFER DIRECTORY [[${CMAKE_SOURCE_DIR}]]
        CALL _uses_certifier_guard_all [[${ARG_TARGET}]]
             [[${CMAKE_SOURCE_DIR}]])")
  endif()
endfunction()

# Find uses-certifier; the configuration fails when it is missing, so a
# build can never skip the check silently.
macro(_uses_certifier_find)
  find_program(USES_CERTIFIER_EXECUTABLE uses-certifier
    DOC "uses-certifier command that checks the code certification")
  if(NOT USES_CERTIFIER_EXECUTABLE)
    message(FATAL_ERROR
      "uses-certifier not found: install it with\n"
      "  pip install git+https://github.com/manvalan/uses-certifier\n"
      "or set USES_CERTIFIER_EXECUTABLE. The build requires certified "
      "code and cannot run without the check.")
  endif()
endmacro()

# The check command line, from the parsed arguments of the caller.
function(_uses_certifier_command out)
  set(command "${USES_CERTIFIER_EXECUTABLE}" check)
  if(ARG_CERTIFICATE)
    list(APPEND command "${ARG_CERTIFICATE}")
  endif()
  if(ARG_AUTHORIZATIONS)
    list(APPEND command --authorizations "${ARG_AUTHORIZATIONS}")
  endif()
  if(ARG_MIN_LEVEL)
    list(APPEND command --min-level "${ARG_MIN_LEVEL}")
  endif()
  set(${out} ${command} PARENT_SCOPE)
endfunction()

# Make the given targets wait for the check.
function(_uses_certifier_guard check)
  foreach(target IN LISTS ARGN)
    add_dependencies(${target} ${check})
  endforeach()
endfunction()

# Make every buildable target of dir and its subdirectories wait for the
# check; runs at the end of the top-level directory.
function(_uses_certifier_guard_all check dir)
  get_property(targets DIRECTORY "${dir}" PROPERTY BUILDSYSTEM_TARGETS)
  foreach(target IN LISTS targets)
    get_property(type TARGET ${target} PROPERTY TYPE)
    if(type MATCHES "^(EXECUTABLE|STATIC_LIBRARY|SHARED_LIBRARY|MODULE_LIBRARY|OBJECT_LIBRARY)$")
      add_dependencies(${target} ${check})
    endif()
  endforeach()
  get_property(subdirs DIRECTORY "${dir}" PROPERTY SUBDIRECTORIES)
  foreach(subdir IN LISTS subdirs)
    _uses_certifier_guard_all(${check} "${subdir}")
  endforeach()
endfunction()
