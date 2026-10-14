// AGP 9+ compiles Kotlin itself; no separate org.jetbrains.kotlin.android
// plugin is applied here (see https://developer.android.com/build/migrate-to-built-in-kotlin).
plugins {
    id("com.android.application") version "9.4.1" apply false
}
