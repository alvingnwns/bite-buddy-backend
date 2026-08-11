import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Image, Dimensions } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';

const { width } = Dimensions.get('window');

export default function AnalysisResult() {
  const router = useRouter();
  const params = useLocalSearchParams();
  
  const foodName = params.foodName || 'Homecook Spaghetti';
  const xpGained = params.xpGained || 0;
  const imageUri = params.imageUri || null;
  const calories = params.calories || 220;
  const sugar = params.sugar || 8;
  const carbs = params.carbs || 42.95;
  const fiber = params.fiber || 2.5;
  const protein = params.protein || 8.06;
  const fat = params.fat || 1.29;

  return (
    <View style={styles.container}>
      {/* Back Button */}
      <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
        <Text style={styles.backBtnText}>{'<'}</Text>
      </TouchableOpacity>
      
      <Text style={styles.pageTitle}>Analysis Result</Text>

      {/* Main Card */}
      <View style={styles.cardContainer}>
        {/* Top Header inside Card */}
        <View style={styles.cardHeader}>
          <Text style={styles.foodNameText}>{foodName}</Text>
          <Text style={styles.aiDetectedText}>AI detected</Text>
        </View>
        
        <Text style={styles.estSugarTitle}>Estimated Sugar Content</Text>
        
        {/* Middle Section: Image & Portion */}
        <View style={styles.middleRow}>
          {/* Image Box */}
          <View style={styles.imageBox}>
            {imageUri ? (
              <Image source={{ uri: imageUri as string }} style={styles.foodImage} />
            ) : (
              <View style={styles.imagePlaceholder} />
            )}
          </View>
          
          {/* Portion Box */}
          <View style={styles.portionBox}>
            <Text style={styles.portionTitle}>Portion size</Text>
            <View style={styles.portionValueRow}>
              <Text style={styles.portionNumber}>180</Text>
              <Text style={styles.portionUnit}>gram</Text>
            </View>
            <TouchableOpacity style={styles.editBtn}>
              <Text style={styles.editBtnText}>Edit</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Sugar Content Badge */}
        <View style={styles.sugarBadge}>
          <Text style={styles.sugarValue}>{sugar} g/portion</Text>
          <View style={styles.sugarCategory}>
            <Text style={styles.sugarCategoryText}>Category: medium</Text>
          </View>
        </View>

        {/* Nutrition Facts Bottom Block */}
        <View style={styles.nutritionBlock}>
          <Text style={styles.nutritionTitle}>Nutrition Facts</Text>
          <View style={styles.nutritionList}>
            <Text style={styles.nutritionText}>Calories: {calories} kkal</Text>
            <Text style={styles.nutritionText}>Carbs: {carbs} gram</Text>
            <Text style={styles.nutritionText}>Fiber: {fiber} gram</Text>
            <Text style={styles.nutritionText}>Protein: {protein} gram</Text>
            <Text style={styles.nutritionText}>Fat: {fat} gram</Text>
            <Text style={styles.xpText}>XP Gained: +{xpGained}</Text>
          </View>
        </View>
      </View>

      {/* Confirm Button */}
      <TouchableOpacity style={styles.confirmBtn} onPress={() => router.replace('/child')}>
        <Text style={styles.confirmBtnText}>Confirm</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F3FEF8',
    alignItems: 'center',
  },
  backBtn: {
    backgroundColor: '#E03B38',
    width: 37,
    height: 37,
    borderRadius: 7,
    justifyContent: 'center',
    alignItems: 'center',
    position: 'absolute',
    top: 50,
    left: 35,
    zIndex: 10,
  },
  backBtnText: { color: 'white', fontWeight: 'bold', fontSize: 18 },
  pageTitle: {
    fontSize: 32,
    fontWeight: '600',
    color: '#0C3638',
    marginTop: 100,
    marginBottom: 20,
  },
  cardContainer: {
    backgroundColor: '#374171',
    width: 324,
    height: 556,
    borderRadius: 20,
    shadowColor: '#374171',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.25,
    shadowRadius: 20,
    elevation: 8,
    position: 'relative',
    marginTop: 10,
  },
  cardHeader: {
    backgroundColor: '#5282BB',
    width: '100%',
    height: 75,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  foodNameText: {
    color: 'white',
    fontSize: 24,
    fontWeight: '600',
  },
  aiDetectedText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
  },
  estSugarTitle: {
    color: '#F9FDFF',
    fontSize: 10,
    fontWeight: '600',
    textAlign: 'center',
    marginTop: 15,
  },
  middleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    marginTop: 15,
  },
  imageBox: {
    width: 133,
    height: 189,
    borderWidth: 5,
    borderColor: '#5282BB',
    borderRadius: 10,
    overflow: 'hidden',
    backgroundColor: '#CCC',
  },
  foodImage: { width: '100%', height: '100%', resizeMode: 'cover' },
  imagePlaceholder: { width: '100%', height: '100%', backgroundColor: '#D9D9D9' },
  portionBox: {
    width: 113,
    height: 189,
    backgroundColor: 'white',
    borderRadius: 10,
    alignItems: 'center',
    paddingTop: 20,
  },
  portionTitle: {
    color: '#374171',
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 10,
  },
  portionValueRow: {
    alignItems: 'center',
    marginBottom: 10,
  },
  portionNumber: {
    color: '#0C3638',
    fontSize: 32,
    fontWeight: 'bold',
  },
  portionUnit: {
    color: '#0C3638',
    fontSize: 13,
    fontWeight: 'bold',
    marginTop: -5,
  },
  editBtn: {
    backgroundColor: '#374171',
    paddingHorizontal: 20,
    paddingVertical: 5,
    borderRadius: 20,
  },
  editBtnText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
  sugarBadge: {
    backgroundColor: '#F3B73B',
    borderWidth: 4,
    borderColor: '#E8F4FF',
    borderRadius: 10,
    width: 257,
    height: 57,
    alignSelf: 'center',
    marginTop: 15,
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
  },
  sugarValue: {
    color: '#FF6200',
    fontSize: 24,
    fontWeight: 'bold',
  },
  sugarCategory: {
    position: 'absolute',
    bottom: -10,
    right: 20,
    backgroundColor: '#E8F4FF',
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 20,
  },
  sugarCategoryText: {
    color: '#E03B38',
    fontSize: 10,
    fontWeight: '600',
  },
  nutritionBlock: {
    backgroundColor: '#D9ECF3',
    width: 324,
    height: 147,
    position: 'absolute',
    bottom: 0,
    borderBottomLeftRadius: 20,
    borderBottomRightRadius: 20,
    alignItems: 'center',
    paddingTop: 15,
  },
  nutritionTitle: {
    color: '#374171',
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 5,
  },
  nutritionList: {
    alignItems: 'flex-start',
  },
  nutritionText: {
    color: '#5282BB',
    fontSize: 13,
    fontWeight: 'bold',
  },
  xpText: {
    color: '#10B981',
    fontSize: 14,
    fontWeight: 'bold',
    marginTop: 5,
  },
  confirmBtn: {
    backgroundColor: '#374171',
    borderWidth: 3,
    borderColor: '#272E51',
    width: 324,
    height: 45,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    position: 'absolute',
    bottom: 40,
    shadowColor: '#374171',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.5,
    shadowRadius: 2,
    elevation: 3,
  },
  confirmBtnText: {
    color: '#E8F4FF',
    fontSize: 24,
    fontWeight: 'bold',
  }
});
