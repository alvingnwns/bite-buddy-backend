import { Stack } from 'expo-router';

export default function ChildLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="index" />
      <Stack.Screen name="scan" />
      <Stack.Screen name="schedule" />
      <Stack.Screen name="meds" />
      <Stack.Screen name="info" />
    </Stack>
  );
}
