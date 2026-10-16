plugins {
    alias(libs.plugins.android.application)
}

android {
    namespace = "com.example.dronebuddyapp"
    compileSdk {
        // version = release(37)
        version = release(36)
    }

    defaultConfig {
        applicationId = "com.example.visualbuddymodern"
        minSdk = 24
        // targetSdk = 37
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
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
    compileOnly("com.dji:dji-sdk-v5-aircraft-provided:5.18.0")
    runtimeOnly("com.dji:dji-sdk-v5-networkImp:5.18.0")

    implementation(libs.androidx.activity.ktx)
    implementation(libs.androidx.appcompat)
    implementation(libs.androidx.constraintlayout)
    implementation(libs.androidx.core.ktx)
    implementation(libs.material)
    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(libs.androidx.junit)
}