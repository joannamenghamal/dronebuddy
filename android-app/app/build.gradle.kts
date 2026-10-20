import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
}

// DJI app keys are tied to a specific developer's account/package name and
// must never be committed - read from the gitignored local.properties
// instead of hardcoding it in the manifest. Fails the build loudly rather
// than silently shipping a placeholder that would fail SDK registration at
// runtime instead of at build time.
//val djiApiKey: String = run {
//    val localProperties = Properties()
//    val localPropertiesFile = rootProject.file("local.properties")
//    if (localPropertiesFile.exists()) {
//        localProperties.load(localPropertiesFile.inputStream())
//    }
//    localProperties.getProperty("DJI_API_KEY")
//        ?: throw GradleException(
//            "Missing DJI_API_KEY in android-bridge/local.properties. " +
//                    "Add a line: DJI_API_KEY=your_key_from_developer.dji.com " +
//                    "(this file is gitignored and never committed)."
//        )
//}

val localProperties = Properties()
val localPropertiesFile = rootProject.file("local.properties")
if (localPropertiesFile.exists()) {
    localProperties.load(localPropertiesFile.inputStream())
}
localProperties.forEach { key, value ->
    project.ext.set(key.toString(), value)
}

fun getLocalProperty(key: String) : String{
    return localProperties.getProperty(key) ?: error("KEY: "+ key +" is missing from local properties")
}

// This is the most important key, so do a callout for it
localProperties.getProperty("DJI_APP_API_KEY")
    ?: throw GradleException(
        "Missing DJI_APP_API_KEY in android-bridge/local.properties. " +
                "Add a line: DJI_APP_API_KEY=your_key_from_developer.dji.com " +
                "(this file is gitignored and never committed)."
    )


android {
    namespace = "com.example.dronebuddyapp"
    compileSdk {
        // version = release(37)
        version = release(36)
    }

    defaultConfig {
        applicationId = "com.example.dronebuddyapp"
        minSdk = 24
        // targetSdk = 37
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        // Manifest Stuff
        manifestPlaceholders["DJI_APP_API_KEY"] = getLocalProperty("DJI_APP_API_KEY")
    }

    buildTypes {
        release {
            optimization {
                enable = false
            }
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

}

dependencies {
    // --- DJI Mobile SDK V5 ---
    // Coordinates and Maven Central hosting verified against
    // search.maven.org / central.sonatype.com for 5.18.0 in this session.
    implementation("com.dji:dji-sdk-v5-aircraft:5.18.0")
    implementation(libs.androidx.gridlayout)
    compileOnly("com.dji:dji-sdk-v5-aircraft-provided:5.18.0")
    runtimeOnly("com.dji:dji-sdk-v5-networkImp:5.18.0")

    implementation(libs.androidx.fragment.ktx)
    implementation(libs.androidx.lifecycle.viewmodel.ktx)
    implementation(libs.androidx.activity.ktx)
    implementation(libs.androidx.appcompat)
    implementation(libs.androidx.constraintlayout)
    implementation(libs.androidx.core.ktx)
    implementation(libs.material)
    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(libs.androidx.junit)
}