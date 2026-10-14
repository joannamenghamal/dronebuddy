# DJI's SDK ships obfuscation/decryption of its own (the Helper.install()
# call in DroneBuddyApplication) and has historically required broad keep
# rules for its own packages under R8/ProGuard. The exact required rule set
# for 5.18.0 is UNVERIFIED in this session - confirm against DJI's own
# sample app's proguard-rules.pro (dji-sdk/Mobile-SDK-Android-V5 repo)
# before shipping a minified release build.
-keep class dji.** { *; }
-keep class com.dji.** { *; }
-keep class com.secneo.** { *; }
-keep class com.cySdkyc.** { *; }
-dontwarn dji.**
