pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        // dji-sdk-v5-aircraft, dji-sdk-v5-aircraft-provided and
        // dji-sdk-v5-networkImp are all published to Maven Central directly
        // (confirmed via search.maven.org / central.sonatype.com as of
        // SDK 5.18.0) - no DJI-specific repository URL is needed.
        mavenCentral()
    }
}

rootProject.name = "dronebuddy-bridge"
include(":app")
