import java.util.Properties

plugins {
    id("com.android.application")
}

// DJI app keys are tied to a specific developer's account/package name and
// must never be committed - read from the gitignored local.properties
// instead of hardcoding it in the manifest. Fails the build loudly rather
// than silently shipping a placeholder that would fail SDK registration at
// runtime instead of at build time.
val djiApiKey: String = run {
    val localProperties = Properties()
    val localPropertiesFile = rootProject.file("local.properties")
    if (localPropertiesFile.exists()) {
        localProperties.load(localPropertiesFile.inputStream())
    }
    localProperties.getProperty("DJI_API_KEY")
        ?: throw GradleException(
            "Missing DJI_API_KEY in android-bridge/local.properties. " +
                "Add a line: DJI_API_KEY=your_key_from_developer.dji.com " +
                "(this file is gitignored and never committed)."
        )
}

android {
    // Must match the package name the DJI app key was registered against on
    // developer.dji.com - a mismatch here fails SDK registration at runtime
    // with INVALID_METADATA, not at build time.
    namespace = "com.example.visualbuddy"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.example.visualbuddy"
        // DJI docs (Mobile-SDK-Tutorial-V5) specify minSdk 23/24+; targetSdk 34
        // was the documented value at the revision checked - raise only after
        // confirming the installed dji-sdk-v5-aircraft version supports it.
        minSdk = 24
        targetSdk = 34

        versionCode = 1
        versionName = "0.1.0"

        manifestPlaceholders["djiApiKey"] = djiApiKey

        // DJI has historically shipped native libraries for arm64-v8a only
        // under MSDK V5 - UNVERIFIED for the exact 5.18.0 release, confirm
        // against the actual aircraft-provided AAR's jni/ contents before
        // relying on this, but including armeabi-v7a/x86_64 when DJI's
        // native libs don't exist for them would crash at load time, not fail
        // to build, so the narrower default is the safer starting point.
        ndk {
            abiFilters += "arm64-v8a"
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        viewBinding = true
        buildConfig = true
    }

    packaging {
        // DJI's provided AAR bundles native libs and metadata that commonly
        // collide with other native-heavy dependencies (OpenCV, etc., if
        // this module ever needs one) - excluded proactively per DJI's own
        // sample project convention. UNVERIFIED against 5.18.0 specifically.
        resources {
            excludes += setOf("META-INF/DEPENDENCIES", "META-INF/LICENSE", "META-INF/LICENSE.txt", "META-INF/NOTICE", "META-INF/NOTICE.txt")
        }
    }
}

dependencies {
    // --- DJI Mobile SDK V5 ---
    // Coordinates and Maven Central hosting verified against
    // search.maven.org / central.sonatype.com for 5.18.0 in this session.
    implementation("com.dji:dji-sdk-v5-aircraft:5.18.0")
    compileOnly("com.dji:dji-sdk-v5-aircraft-provided:5.18.0")
    runtimeOnly("com.dji:dji-sdk-v5-networkImp:5.18.0")

    // --- Python <-> Android bridge transport (see /DRONE_BRIDGE.md) ---
    implementation("org.java-websocket:Java-WebSocket:1.5.6")

    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
}
